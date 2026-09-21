from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .config import DEFAULT_ROSTER, ENV_KEYS, MODELS, SMALL_TIER, MID_TIER
from .metrics import agreement, macro_f1, op_metrics, pooled_metrics, question_metrics
from .providers import make_provider, parse_model_key
from .runner import job_path, load_predictions, parse_job_stem, run_jobs
from .tasks import TaskSet, load_corpus

app = typer.Typer(no_args_is_help=True, help="Jev vs LLMs on eDiscovery classification.")
console = Console(width=220)
load_dotenv()


def _expand_models(keys: list[str] | None) -> list[str]:
    if not keys:
        return list(DEFAULT_ROSTER)
    out: list[str] = []
    for k in keys:
        for part in k.split(","):
            part = part.strip()
            if part == "all":
                out += DEFAULT_ROSTER
            elif part == "small":
                out += SMALL_TIER
            elif part == "mid":
                out += MID_TIER
            elif part == "llms":
                out += SMALL_TIER + MID_TIER
            elif part == "jev-ablations":
                from .providers.typesafe import VARIANTS

                out += [f"jev@{v}" for v in VARIANTS if v != "recipe"]
            elif part == "laya":
                out += ["laya@base", "laya@choice", "laya@score", "laya@compact", "laya@chunk", "laya@recipe",
                        "laya-typed@base", "laya-typed@recipe", "laya-multilingual@base", "laya-multilingual@recipe"]
            elif part == "laya-ablations":
                from .providers.laya_ import LAYA_VARIANTS

                out += [f"laya@{v}" for v in LAYA_VARIANTS]
            elif part == "floors":
                out += ["lexical", "laya@base", "laya-typed@base", "gemma3-12b"]
            elif part:
                parse_model_key(part)  # validates
                out.append(part)
    seen = set()
    return [k for k in out if not (k in seen or seen.add(k))]


@app.command()
def models():
    """List the model roster and pricing."""
    t = Table(title="Model roster (USD per 1M tokens)")
    for c in ["key", "provider", "wire id", "tier", "effort", "in $", "out $", "key set?"]:
        t.add_column(c)
    for m in MODELS.values():
        has = "—" if not ENV_KEYS[m.provider] else ("yes" if os.environ.get(ENV_KEYS[m.provider]) else "[red]no[/red]")
        t.add_row(m.key, m.provider, m.model_id, m.size, m.effort or "default", f"{m.input_per_mtok:g}", f"{m.output_per_mtok:g}", has)
    console.print(t)
    console.print(f"Default roster: {', '.join(DEFAULT_ROSTER)}")
    from .providers.typesafe import VARIANTS

    console.print(f"Jev variants: {', '.join('jev@'+v for v in VARIANTS)}")


@app.command()
def doctor(model: Optional[list[str]] = typer.Option(None, "--model", "-m")):
    """One tiny classification call per model to prove auth + connectivity."""
    keys = _expand_models(model)

    async def check(k):
        spec, _ = parse_model_key(k)
        env = ENV_KEYS[spec.provider]
        if env and not os.environ.get(env):
            return k, f"[yellow]skipped[/yellow]  {env} not set"
        try:
            p = make_provider(k)
            try:
                return k, "[green]" + await p.healthcheck() + "[/green]"
            finally:
                await p.aclose()
        except Exception as e:  # noqa: BLE001
            return k, f"[red]FAIL[/red]  {type(e).__name__}: {e}"

    async def run_all():
        return await asyncio.gather(*(check(k) for k in keys))

    for k, s in asyncio.run(run_all()):
        console.print(f"{k:<24} {s}")


@app.command()
def run(
    task: Path = typer.Option(..., "--task", "-t", help="Task-set YAML"),
    data: Path = typer.Option(..., "--data", "-d", help="Corpus JSONL"),
    corpus: Optional[str] = typer.Option(None, "--corpus", help="Corpus name for results dir (default: data file stem)"),
    model: Optional[list[str]] = typer.Option(None, "--model", "-m", help="Model keys; groups: all, small, mid, llms, jev-ablations"),
    arm: list[str] = typer.Option(["single"], "--arm", "-a", help="single and/or multi"),
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n"),
    questions: Optional[str] = typer.Option(None, "--questions", "-q", help="Comma-separated question ids (default all)"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
    effort: Optional[str] = typer.Option(None, "--effort", help="LLM effort override; 'default' = vendor default"),
    phrasing: str = typer.Option("rfp", "--phrasing", help="rfp | literal (LLM prompt phrasing)"),
    batch: bool = typer.Option(False, "--batch", help="Use Anthropic Message Batches (50% off, no latency)"),
    no_flex: bool = typer.Option(False, "--no-flex", help="Disable OpenAI flex tier"),
    temperature: Optional[float] = typer.Option(None, "--temperature", help="LLM sampling temperature override (vendor default if unset)"),
    tag: str = typer.Option("", "--tag", help="Suffix for the results file (e.g. effort_default)"),
    unlabeled: bool = typer.Option(False, "--unlabeled", help="Corpus has no gold labels"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Run models over a corpus. Resumable."""
    ts = TaskSet.load(task)
    if questions:
        ts = ts.subset([q.strip() for q in questions.split(",")])
    docs = load_corpus(data, limit=limit, labeled=not unlabeled)
    keys = _expand_models(model)
    corpus = corpus or data.stem
    n_units = len(docs) * sum(len(ts.qids) if a == "single" else 1 for a in arm)
    console.print(f"[bold]{ts.name}[/bold] · {len(docs)} docs · {len(ts.qids)} questions · arms={arm} · {n_units} calls/model · models: {', '.join(keys)}")
    if not yes and not typer.confirm("Proceed?", default=False):
        raise typer.Exit(1)
    asyncio.run(
        run_jobs(ts, docs, keys, arm, out, corpus, concurrency=concurrency, effort=effort, phrasing=phrasing, batch=batch, flex=not no_flex, temperature=temperature, tag=tag)
    )
    _report(ts, out, corpus, arm, keys, tag)


@app.command()
def sample(
    data: Path = typer.Option(..., "--data", "-d"),
    out: Path = typer.Option(..., "--out", "-o"),
    n: int = typer.Option(100, "--n"),
    min_pos: int = typer.Option(8, "--min-pos", help="Minimum positives per question where available"),
    seed: int = typer.Option(3, "--seed"),
):
    """Stratified subsample of a labeled corpus (for pilots / dev splits)."""
    import random

    rows = [json.loads(l) for l in data.read_text().splitlines() if l.strip()]
    rng = random.Random(seed)
    rng.shuffle(rows)
    qids = sorted({q for r in rows for q in (r.get("labels") or {})})
    chosen: list[dict] = []
    ids: set[str] = set()
    for q in qids:
        pos = [r for r in rows if q in (r.get("labels") or {}) and r["id"] not in ids]
        for r in pos[:min_pos]:
            chosen.append(r); ids.add(r["id"])
    for r in rows:
        if len(chosen) >= n:
            break
        if r["id"] not in ids:
            chosen.append(r); ids.add(r["id"])
    rng.shuffle(chosen)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in chosen))
    counts = {q: sum(1 for r in chosen if q in (r.get("labels") or {})) for q in qids}
    console.print(f"wrote {len(chosen)} docs to {out}; positives per question: {counts}")


@app.command("laya-ft")
def laya_ft(
    task: Path = typer.Option(..., "--task", "-t"),
    data: Path = typer.Option(..., "--data", "-d", help="Full labeled corpus; split is written next to it"),
    out: Path = typer.Option(..., "--out", "-o", help="Model output dir, e.g. models/laya-ft-veridian"),
    frac_train: float = typer.Option(0.30, "--frac-train"),
    seed: int = typer.Option(11, "--seed"),
    epochs: int = typer.Option(3, "--epochs"),
    device: Optional[str] = typer.Option(None, "--device"),
    split_only: bool = typer.Option(False, "--split-only"),
    train_file: Optional[Path] = typer.Option(None, "--train", help="Use this labeled file as the train split instead of splitting --data (e.g. TREC dev.jsonl); --data is then the test set"),
):
    """SUPERVISED: split a corpus by document and fine-tune Laya on the dev split (RLCD recipe)."""
    from .laya_ft import make_split, train

    if train_file is not None:
        p_tr, p_te = train_file, data
    else:
        p_tr, p_te = make_split(data, data.parent, frac_train, seed)
    n_tr = sum(1 for _ in p_tr.open()); n_te = sum(1 for _ in p_te.open())
    console.print(f"split: {n_tr} train docs -> {p_tr}; {n_te} test docs -> {p_te}")
    if split_only:
        return
    train(task, p_tr, out, device=device, log=console.print, epochs=epochs)


@app.command()
def goldify(
    data: Path = typer.Option(..., "--data", "-d", help="Unlabeled corpus JSONL"),
    out: Path = typer.Option(..., "--out", "-o", help="Labeled corpus JSONL"),
    corpus: str = typer.Option(..., "--corpus"),
    results: Path = typer.Option(Path("results"), "--results"),
    arm: str = typer.Option("multi", "--arm"),
    model: list[str] = typer.Option(..., "--model", "-m", help="Panel members (prediction files must exist)"),
    tag: str = typer.Option("", "--tag"),
    positive: str = typer.Option("responsive"),
):
    """Build provisional gold labels from an LLM panel: majority vote; gray where the panel splits
    or the mean probability is in [0.35, 0.65]. Writes panel votes into meta.panel."""
    keys = _expand_models(model)
    votes: dict[tuple[str, str], list[tuple[str, str, float]]] = {}
    for k in keys:
        f = job_path(results, corpus, arm, k, tag)
        if not f.exists():
            raise typer.BadParameter(f"missing predictions {f}")
        for p in load_predictions(f):
            if not p.error:
                votes.setdefault((p.doc_id, p.question), []).append((k, p.label, p.p_positive))
    by_doc: dict[str, dict[tuple[str, str], list]] = {}
    for (d, q), vs in votes.items():
        by_doc.setdefault(d, {})[(d, q)] = vs
    rows = [json.loads(l) for l in data.read_text().splitlines() if l.strip()]
    n_pos: dict[str, int] = {}; n_gray: dict[str, int] = {}
    with out.open("w") as f:
        for r in rows:
            labels: dict[str, str] = {}; gray: list[str] = []; panel: dict[str, dict] = {}
            for (d, q), vs in by_doc.get(r["id"], {}).items():
                yes = sum(1 for _, lab, _ in vs if lab == positive)
                mean_p = sum(p for _, _, p in vs) / len(vs)
                panel[q] = {k: round(p, 3) for k, _, p in vs}
                if yes * 2 > len(vs):
                    labels[q] = positive; n_pos[q] = n_pos.get(q, 0) + 1
                if (0 < yes < len(vs)) or 0.35 <= mean_p <= 0.65:
                    gray.append(q); n_gray[q] = n_gray.get(q, 0) + 1
            r["labels"] = labels; r["gray"] = sorted(gray)
            r.setdefault("meta", {})["panel"] = panel
            f.write(json.dumps(r) + "\n")
    console.print(f"wrote {len(rows)} docs → {out}")
    for q in sorted(set(n_pos) | set(n_gray)):
        console.print(f"  {q:<28} positives={n_pos.get(q,0):<5} gray={n_gray.get(q,0)}")


CUAD_CATEGORIES = {
    "License Grant": "license_grant",
    "Non-Transferable License": "nontransferable_license",
    "Anti-Assignment": "anti_assignment",
    "Cap On Liability": "cap_on_liability",
    "Minimum Commitment": "minimum_commitment",
    "Revenue/Profit Sharing": "revenue_profit_sharing",
    "Audit Rights": "audit_rights",
    "Exclusivity": "exclusivity",
    "Insurance": "insurance",
    "Change Of Control": "change_of_control",
    "Ip Ownership Assignment": "ip_ownership_assignment",
    "Non-Compete": "non_compete",
}


@app.command("cuad-build")
def cuad_build(
    out: Path = typer.Option(Path("data/cuad/cuad.jsonl"), "--out", "-o"),
    cache: Path = typer.Option(Path("data/cuad/raw"), "--cache", help="Where CUAD test.json is downloaded"),
):
    """Build the CUAD paragraph corpus (official test split, 12 clause categories) with human gold."""
    from .cuad.build import build

    out.parent.mkdir(parents=True, exist_ok=True)
    build(cache, out, CUAD_CATEGORIES)


@app.command("trec-build")
def trec_build(
    out_dir: Path = typer.Option(Path("data/trec"), "--out"),
    full: bool = typer.Option(False, "--full", help="Also write full.jsonl (all ~290k emails; ~800 MB)"),
):
    """Build the TREC Total Recall (Jeb Bush) dev / eval / full corpora from NIST judgments."""
    from .trec.build import build_dev, build_eval, build_full

    seen = set()
    p = out_dir / "seen_ids.txt"
    if p.exists():
        seen = {str(int(x)) for x in p.read_text().split() if x.strip()}
    dev = build_dev(out_dir / "dev.jsonl", seen=seen)
    (out_dir / "dev_ids.txt").write_text("\n".join(sorted(dev, key=int)) + "\n")
    build_eval(out_dir / "eval.jsonl", exclude=dev | seen)
    if full:
        build_full(out_dir / "full.jsonl", exclude=dev | seen)


@app.command()
def audit_merge(
    data: Path = typer.Option(..., "--data", "-d", help="Planner-labeled corpus (writer output)"),
    out: Path = typer.Option(..., "--out", "-o"),
    corpus: str = typer.Option(..., "--corpus"),
    results: Path = typer.Option(Path("results"), "--results"),
    model: list[str] = typer.Option(..., "--model", "-m", help="Auditor panel"),
    tag: str = typer.Option("audit", "--tag"),
    arm: str = typer.Option("multi", "--arm"),
    positive: str = typer.Option("responsive"),
):
    """Reconcile planner-intent labels with an auditor panel that read the rendered text.

    Rules (P = planner label, A = auditor majority; `allowed` = RFPs the planner could assign in that arc):
      P=yes, all auditors no  -> gold no, gray      (writer dropped the responsive content)
      P=yes, split            -> gold yes, gray
      P=no,  all yes, outside allowed -> gold yes   (planner never considered this RFP)
      P=no,  all yes, inside allowed  -> gold no, gray (planner's intentional hard negative; disputed)
      P=no,  split, outside allowed   -> gold no, gray
      otherwise planner label stands.
    """
    from .synth.plan import ARCS, RFP_NUM

    keys = _expand_models(model)
    votes: dict[str, dict[str, list[tuple[str, str, float]]]] = {}
    for k in keys:
        f = job_path(results, corpus, arm, k, tag)
        if not f.exists():
            raise typer.BadParameter(f"missing predictions {f}")
        for p in load_predictions(f):
            if not p.error:
                votes.setdefault(p.doc_id, {}).setdefault(p.question, []).append((k, p.label, p.p_positive))
    rows = [json.loads(l) for l in data.read_text().splitlines() if l.strip()]
    qids = list(RFP_NUM.values())
    stats = {"flip_to_no": 0, "flip_to_yes": 0, "new_gray": 0}
    with out.open("w") as f:
        for r in rows:
            arc = r["meta"]["arc"]
            allowed = {RFP_NUM[n] for n in ARCS[arc]["allowed"] if n in RFP_NUM}
            labels = dict(r["labels"]); gray = set(r.get("gray") or []); audit: dict[str, dict] = {}
            planner_labels = sorted(labels)
            for q in qids:
                vs = votes.get(r["id"], {}).get(q, [])
                if not vs:
                    continue
                yes = sum(1 for _, lab, _ in vs if lab == positive); n = len(vs)
                audit[q] = {k: round(p, 3) for k, _, p in vs}
                P = q in labels
                if P and yes == 0:
                    labels.pop(q); gray.add(q); stats["flip_to_no"] += 1
                elif P and yes < n:
                    if q not in gray: stats["new_gray"] += 1
                    gray.add(q)
                elif not P and yes == n:
                    if q not in allowed:
                        labels[q] = positive; stats["flip_to_yes"] += 1
                    else:
                        if q not in gray: stats["new_gray"] += 1
                        gray.add(q)
                elif not P and yes > 0 and q not in allowed:
                    if q not in gray: stats["new_gray"] += 1
                    gray.add(q)
            r["labels"] = labels; r["gray"] = sorted(gray)
            r["meta"]["planner_labels"] = planner_labels
            r["meta"]["audit"] = audit
            f.write(json.dumps(r) + "\n")
    console.print(f"wrote {len(rows)} docs → {out}; {stats}")
    from collections import Counter
    c = Counter(q for r in rows for q in r["labels"]); g = Counter(q for r in rows for q in r["gray"])
    for q in qids:
        console.print(f"  {q:<26} pos={c[q]:<5} gray={g[q]}")


@app.command()
def report(
    task: Path = typer.Option(..., "--task", "-t"),
    corpus: str = typer.Option(..., "--corpus"),
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    arm: list[str] = typer.Option(["single"], "--arm", "-a"),
    model: Optional[list[str]] = typer.Option(None, "--model", "-m"),
    tag: str = typer.Option("", "--tag"),
    exclude_gray: bool = typer.Option(False, "--exclude-gray"),
    per_question: bool = typer.Option(False, "--per-question", "-Q"),
    data: Optional[Path] = typer.Option(None, "--data", "-d", help="Rebind gold/gray from this corpus file"),
):
    """Recompute tables from saved predictions."""
    ts = TaskSet.load(task)
    keys = _expand_models(model) if model else None
    docs = load_corpus(data) if data else None
    _report(ts, out, corpus, arm, keys, tag, exclude_gray, per_question, docs)


def rebind_gold(preds, docs, ts):
    by = {d.id: d for d in docs}
    out = []
    for p in preds:
        d = by.get(p.doc_id)
        if d is None:
            continue
        p.gold = d.gold(p.question, ts.negative_label)
        p.gray = p.question in d.gray
        out.append(p)
    return out


@app.command()
def writeup(
    task: Path = typer.Option(..., "--task", "-t"),
    data: Path = typer.Option(..., "--data", "-d"),
    corpus: str = typer.Option(..., "--corpus"),
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    arm: list[str] = typer.Option(["single", "multi"], "--arm", "-a"),
    tag: list[str] = typer.Option([""], "--tag"),
    title: Optional[str] = typer.Option(None, "--title"),
):
    """Write results/<corpus>/REPORT.md from saved predictions."""
    from .writeup import write_report

    p = write_report(task, data, out, corpus, tuple(arm), tuple(tag), title)
    console.print(f"wrote {p}")


@app.command("jev-recipe")
def jev_recipe(
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    dest: Path = typer.Option(Path("design/05_jev_recipe.md"), "--dest"),
):
    """Jev ablation across all corpora; pick the recipe on the Veridian dev split and confirm elsewhere."""
    from .recipe import write_recipe

    console.print(f"wrote {write_recipe(out, dest)}")


@app.command("export-findings")
def export_findings(
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    dest: Path = typer.Option(Path("results/findings.json"), "--dest"),
):
    """Speed, cost, recall/precision (Wilson CIs) per corpus/arm/model -> findings.json."""
    from .export import export

    console.print(f"wrote {export(out, dest)}")


@app.command("export-examples")
def export_examples(
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    dest: Path = typer.Option(Path("results/examples.json"), "--dest"),
):
    """Worked request/response examples per configuration for the site's explainer modal -> examples.json."""
    from .examples import export

    export(out, dest)
    console.print(f"wrote {dest}")


@app.command("det-sample")
def det_sample(
    src: Path = typer.Option(Path("data/mallinckrodt/mnk.jsonl"), "--src"),
    dst: Path = typer.Option(Path("data/mallinckrodt/det300.jsonl"), "--dst"),
    per_stratum: int = typer.Option(100, "--per-stratum"),
):
    """Stratified (gray / clear positive / clear negative) sample for the determinism study."""
    from .determinism import build_sample

    console.print_json(json.dumps(build_sample(src, dst, per_stratum=per_stratum)))


@app.command("determinism")
def determinism(
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    sample: Path = typer.Option(Path("data/mallinckrodt/det300.jsonl"), "--sample"),
    corpus: Path = typer.Option(Path("data/mallinckrodt/mnk.jsonl"), "--corpus"),
    dest: Path = typer.Option(Path("results/determinism.json"), "--dest"),
):
    """Run-to-run flip rates per model from the repeat runs in results/mnk_det -> determinism.json."""
    from .determinism import analyze

    res = analyze(out, sample, corpus)
    dest.write_text(json.dumps(res, indent=1))
    t = Table(title="Determinism: label disagreement across repeat runs")
    for c in ["arm", "setting", "model", "K", "decisions", "flip %", "pairwise %", "doc flip %", "identical p %", "conf. flip %", "recall range"]:
        t.add_column(c, justify="right" if c not in ("arm", "setting", "model") else "left")
    for c in res["cells"]:
        t.add_row(
            c["arm"], c["setting"], c["model"], str(c["k"]), str(c["n_decisions"]),
            _fmt(c["decision_flip"][0], pct=True), _fmt(c["pairwise"][0], pct=True),
            _fmt(c.get("doc_flip", [None])[0], pct=True) if c.get("doc_flip") else "—",
            _fmt(c["identical_prob"][0], pct=True), _fmt(c["confident_flip"][0], pct=True),
            f"{c['recall_range'][0]*100:.1f}–{c['recall_range'][1]*100:.1f}" if c["recall_range"] else "—",
        )
    console.print(t)
    console.print(f"wrote {dest}")


def _fmt(v, pct=False, nd=3):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{v*100:.1f}" if pct else f"{v:.{nd}f}"


def _report(ts, out: Path, corpus: str, arms, keys, tag="", exclude_gray=False, per_question=False, docs=None):
    pos = ts.positive_label
    found: dict[str, list] = {}
    for a in arms:
        d = out / corpus / a
        if not d.exists():
            continue
        for f in sorted(d.glob("*.jsonl")):
            mk, ftag = parse_job_stem(f.stem)
            if ftag != tag:
                # tagged files (e.g. pilots) are excluded unless asked for
                continue
            if keys and mk not in keys:
                continue
            preds = load_predictions(f)
            if docs is not None:
                preds = rebind_gold(preds, docs, ts)
            if preds:
                found[f"{mk} [{a}]"] = preds
    if not found:
        console.print("[red]no predictions found[/red]")
        return

    for gray_mode in ([False, True] if not exclude_gray else [True]):
        title = f"{corpus}: pooled over {len(ts.qids)} questions" + (" (gray excluded)" if gray_mode else " (all gold)")
        tbl = Table(title=title)
        for c in ["model [arm]", "n", "err", "prec", "recall", "F1", "macroF1", "elusion", "κ", "ROC", "PR-AUC", "Brier", "ECE", "bestF1@thr"]:
            tbl.add_column(c, justify="left" if c.startswith("model") else "right")
        summaries = {}
        for k, preds in found.items():
            pm = pooled_metrics(preds, pos, gray_mode)
            qms = [question_metrics(q, preds, pos, gray_mode) for q in ts.qids]
            summaries[k] = {"pooled": pm.to_dict(), "questions": {q.question: q.to_dict() for q in qms}, "ops": op_metrics(preds).to_dict()}
            tbl.add_row(k, str(pm.n), str(pm.n_errors), _fmt(pm.precision, True), _fmt(pm.recall, True), _fmt(pm.f1, True),
                        _fmt(macro_f1(qms), True), _fmt(pm.elusion, True), _fmt(pm.kappa), _fmt(pm.roc_auc), _fmt(pm.pr_auc),
                        _fmt(pm.brier), _fmt(pm.ece), f"{_fmt(pm.best_f1, True)}@{_fmt(pm.best_f1_threshold, nd=2)}")
        console.print(tbl)
        suffix = "_nogray" if gray_mode else ""
        p = out / corpus / f"summary{('_'+tag) if tag else ''}{suffix}.json"
        p.write_text(json.dumps(summaries, indent=2, default=str))

        if per_question:
            for k, preds in found.items():
                t2 = Table(title=f"{k} by question" + (" (gray excluded)" if gray_mode else ""))
                for c in ["question", "n", "pos", "prec", "recall", "95% CI", "F1", "ROC", "Brier", "bestF1@thr"]:
                    t2.add_column(c, justify="left" if c == "question" else "right")
                for q in ts.qids:
                    m = question_metrics(q, preds, pos, gray_mode)
                    ci = f"[{m.recall_ci[0]*100:.0f},{m.recall_ci[1]*100:.0f}]" if m.recall_ci else "—"
                    t2.add_row(q, str(m.n), str(m.n_pos), _fmt(m.precision, True), _fmt(m.recall, True), ci, _fmt(m.f1, True), _fmt(m.roc_auc), _fmt(m.brier), f"{_fmt(m.best_f1, True)}@{_fmt(m.best_f1_threshold, nd=2)}")
                console.print(t2)

    tbl = Table(title=f"{corpus}: speed and cost (per (doc,question) decision)")
    for c in ["model [arm]", "resolved", "p50 ms", "p95 ms", "in tok", "cached", "out tok", "paid $", "list $", "list $/1k", "mode"]:
        tbl.add_column(c, justify="left" if c in ("model [arm]", "resolved", "mode") else "right")
    for k, preds in found.items():
        o = op_metrics(preds)
        res = next((p.model_resolved for p in preds if not p.error), "")
        tbl.add_row(k, res, _fmt(o.latency_p50_ms, nd=0), _fmt(o.latency_p95_ms, nd=0), f"{o.input_tokens_mean:,.0f}", f"{o.cached_tokens_mean:,.0f}",
                    f"{o.output_tokens_mean:,.0f}", f"{o.total_cost_usd:.3f}", f"{o.total_list_cost_usd:.3f}", f"{o.cost_per_1k_docs_usd:.3f}",
                    ",".join(f"{m}:{n}" for m, n in o.pricing_modes.items()))
    console.print(tbl)

    if len(found) > 1:
        ks = list(found)
        tbl = Table(title="inter-model agreement (Cohen's κ on labels)")
        tbl.add_column("")
        for k in ks:
            tbl.add_column(k[:14], justify="right")
        for a in ks:
            tbl.add_row(a, *[_fmt(agreement(found[a], found[b]), nd=2) for b in ks])
        console.print(tbl)


if __name__ == "__main__":
    app()

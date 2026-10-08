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
            elif part == "openai-decisions":
                out += ["openai-decisions@choice", "openai-decisions@predicate", "openai-decisions@decompose"]
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


@app.command("legal-build")
def legal_build(
    which: str = typer.Option("all", "--which", "-w", help="legal10 | learn | legal09 | all"),
    msg: bool = typer.Option(False, "--msg", help="Also build the message-unit files (default is the document unit)"),
):
    """Build the TREC Legal 2009/2010 corpora from the NIST qrels and the EDRM v2 text rendering (EDRM/)."""
    from .legal.build import EDRM_TAR, build_legal09_ids, build_legal10, build_legal10_learn

    log = console.print
    if which in ("legal09", "all"):
        build_legal09_ids(unit="doc", log=log)
        if msg:
            build_legal09_ids(unit="msg", log=log)
    if which in ("legal10", "learn", "all") and not EDRM_TAR.exists():
        raise typer.BadParameter(f"{EDRM_TAR} not found; download edrmv2txt-v2.tar.bz2 from trec-legal.umiacs.umd.edu/corpora/trec/legal10/")
    if which in ("legal10", "all"):
        build_legal10(unit="doc", log=log)
        if msg:
            build_legal10(unit="msg", log=log)
    if which in ("learn", "all"):
        build_legal10_learn(log=log)


# ---- training-data contamination probe (design/06_contamination_probe.md) ----------------------

CONTAM_ROSTER = ["claude-haiku-4.5", "gpt-5.6-luna", "gemini-3.5-flash-lite", "claude-sonnet-5", "gpt-5.6-terra", "gemini-3.8-flash"]


@app.command("contam-build")
def contam_build(
    n_verbatim: int = typer.Option(60, "--n-verbatim", help="Documents per corpus for the verbatim-continuation probe"),
    seed: int = typer.Option(7, "--seed"),
):
    """Build data/contam/probes.jsonl: verbatim, entity, benchmark-knowledge and label-recall items for every corpus."""
    from .contam.build import build

    build(n_verbatim=n_verbatim, seed=seed, log=console.print)


@app.command("contam-run")
def contam_run(
    model: Optional[list[str]] = typer.Option(None, "--model", "-m", help="Model keys (default: the six small/mid roster LLMs)"),
    probe: Optional[list[str]] = typer.Option(None, "--probe", "-p", help="verbatim | entity_recall | entity_recog | bench_knowledge | label_recall"),
    corpus: Optional[list[str]] = typer.Option(None, "--corpus", "-c", help="enron | jebbush | mnk | veridian | cuad"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Pilot: at most N items per (probe, corpus)"),
    concurrency: int = typer.Option(8, "--concurrency"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Run the contamination probe items against the LLMs (resumable; results/contam/<model>.jsonl)."""
    from .contam.run import load_items, run_models

    keys = _expand_models(model) if model else list(CONTAM_ROSTER)
    items = load_items(probes=probe, corpora=corpus, limit=limit)
    in_tok = sum(len(i["system"]) + len(i["user"]) for i in items) / 4
    console.print(f"{len(items)} items x {len(keys)} models; ~{in_tok/1e3:.0f}k input tokens per model")
    for k in keys:
        s = MODELS[k]
        if not os.environ.get(ENV_KEYS[s.provider]):
            raise typer.BadParameter(f"{k}: {ENV_KEYS[s.provider]} not set")
        console.print(f"  {k:24s} ~${s.cost_usd(int(in_tok), int(len(items) * 60)):.2f}")
    if not yes and not typer.confirm("Proceed?"):
        raise typer.Abort()
    res = asyncio.run(run_models(keys, items, concurrency=concurrency, log=console.print))
    for r in res:
        console.print(r)


@app.command("contam-report")
def contam_report(
    model: Optional[list[str]] = typer.Option(None, "--model", "-m"),
):
    """Score results/contam/*.jsonl -> results/contam/summary.json and REPORT.md."""
    from .contam.run import RESULTS_DIR
    from .contam.score import score_all

    keys = _expand_models(model) if model else [p.stem for p in sorted(RESULTS_DIR.glob("*.jsonl")) if p.stem in MODELS]
    score_all(keys, log=console.print)
    console.print((RESULTS_DIR / "REPORT.md").read_text())


@app.command("contam-html")
def contam_html():
    """Render results/contam/summary.json as a self-contained HTML report (methodology, charts, tables)."""
    from .contam.html import build_html
    from .contam.run import RESULTS_DIR

    summary = json.loads((RESULTS_DIR / "summary.json").read_text())
    out = build_html(summary)
    console.print(f"wrote {out}")


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
    from .scope import in_scope

    ts = TaskSet.load(task)
    keys = _expand_models(model) if model else None
    docs = in_scope(corpus, load_corpus(data)) if data else None
    _report(ts, out, corpus, arm, keys, tag, exclude_gray, per_question, docs)


def rebind_gold(preds, docs, ts):
    by = {d.id: d for d in docs}
    out = []
    for p in preds:
        d = by.get(p.doc_id)
        if d is None or p.question not in ts.questions:  # dropped question (TREC eminent_domain): not scored
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
    carry: bool = typer.Option(True, "--carry/--no-carry", help="Keep records of --dest whose result file is absent under --out (warns); --no-carry rebuilds from the files alone"),
):
    """Speed, cost, recall/precision (Wilson CIs) per corpus/arm/model -> findings.json."""
    from .export import export

    console.print(f"wrote {export(out, dest, carry)}")


@app.command("export-sweep")
def export_sweep_cmd(
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    dest: Path = typer.Option(Path("results/sweep.json"), "--dest"),
    check: bool = typer.Option(True, "--check/--no-check", help="Score each cell at its own label and compare with findings.json"),
    arms: list[str] = typer.Option(["multi"], "--arm", help="Arms to export (default: multi, the arm the site's recall/precision charts draw)"),
):
    """Recall/precision confusion counts at p(responsive) >= t, t = 0.05..0.95, per corpus/arm/model -> sweep.json (the Studio's threshold slider)."""
    from .sweep import export_sweep

    console.print(f"wrote {export_sweep(out, dest, check, tuple(arms))}")


@app.command("export-study")
def export_study_cmd(
    findings: Path = typer.Option(Path("results/findings.json"), "--findings"),
    dest: Path = typer.Option(Path("results/study.json"), "--dest"),
):
    """Human-anchored study: datasets x experiments x arms -> study.json (site/study.html). Unrun cells are flagged placeholders."""
    from .study import export_study

    console.print(f"wrote {export_study(findings, dest)}")


@app.command("export-explore")
def export_explore_cmd(
    dest: Path = typer.Option(Path("site/public/explore"), "--dest"),
    results: Path = typer.Option(Path("results"), "--results"),
    only: list[str] = typer.Option([], "--only", help="Dataset ids to export (default: all with data on disk)"),
):
    """Population explorer: per-judgment rows and per-arm scores -> site/public/explore/ (site/explore.html). Unrun arms are flagged placeholders."""
    from .explore import export_explore

    for p in export_explore(dest, results, set(only) or None):
        console.print(f"wrote {p}")


@app.command("serve")
def serve_cmd(port: int = typer.Option(8766, "--port", "-p"), no_warm: bool = typer.Option(False, "--no-warm", help="Index datasets on first request instead of at start")):
    """Serve document text to the population explorer from data/ on 127.0.0.1 (text is never exported to the site)."""
    from .serve import serve

    serve(port, warm=not no_warm)


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
            preds = [p for p in load_predictions(f) if p.question in ts.questions]
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



@app.command("tar")
def tar_cmd(
    corpus: str = typer.Argument(..., help="mnk | cuad | trec"),
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    only: str = typer.Option(None, "--only", help="variant name or prefix (e.g. t1_100 or cal), 'accuracy' for the reviewer-accuracy sweep, or 'new-depths' for requested 7,500/10,000 TREC variants"),
    seeds: int = typer.Option(5, "--seeds"),
):
    """Classical TAR baselines (TF-IDF + logistic regression, simulated reviewer) -> results/<corpus>/multi/tar__*.jsonl."""
    from .tar import run_corpus

    run_corpus(corpus, out, only, seeds)


@app.command("tar-grid")
def tar_grid_cmd(
    corpus: str = typer.Argument(..., help="mnk | cuad | trec"),
    variant: list[str] = typer.Option(["t1_1000_div", "cal"], "--variant", help="TAR variants to sweep (default: the two headline workflows)"),
    fn: list[float] = typer.Option([], "--fn", help="Reviewer miss rates (default 0 .05 .10 .20 .30 .40 .50)"),
    fp: list[float] = typer.Option([], "--fp", help="Reviewer over-code rates (default 0 .01 .02 .05 .10 .15 .20)"),
    seeds: int = typer.Option(5, "--seeds"),
    out: Path = typer.Option(Path("results/tar_grid"), "--out", "-o"),
    results: Path = typer.Option(Path("results"), "--results", help="Where the corpus runs live (keyword-floor scores for CAL)"),
    fp_max: Optional[float] = typer.Option(None, "--fp-max", help="Leave over-code rates above this out of the cells and record them as `unavailable` (TREC CAL: 0.02; above it the control-set stop rule does not converge on the 286k pool)"),
):
    """Reviewer miss-rate x over-code-rate grid for the TAR workflows -> results/tar_grid/<corpus>__<variant>.json, then results/tar_grid.json.
    The default cell is checked against findings.json (same rows, same scoring)."""
    from .tar import FN_GRID, FP_GRID, export_grid, run_grid

    for p in run_grid(corpus, tuple(variant), tuple(fn) or FN_GRID, tuple(fp) or FP_GRID, seeds, out, results, fp_max=fp_max):
        console.print(f"wrote {p}")
    console.print(f"wrote {export_grid(out)}")


@app.command("export-tar-grid")
def export_tar_grid_cmd(
    src: Path = typer.Option(Path("results/tar_grid"), "--src"),
    dest: Path = typer.Option(Path("results/tar_grid.json"), "--dest"),
):
    """Fold results/tar_grid/<corpus>__<variant>.json into results/tar_grid.json (corpus -> variant), imported by the site next to findings.json."""
    from .tar import export_grid

    console.print(f"wrote {export_grid(src, dest)}")


if __name__ == "__main__":
    app()


@app.command("contam-paper")
def contam_paper():
    """Render results/contam/summary.json as an arXiv-style paper (paper.html) and a short plain-language explainer (explainer.html)."""
    from .contam.brief import build_lawyer_guide, build_short_report
    from .contam.paper import build_explainer, build_paper
    from .contam.run import RESULTS_DIR
    from .contam.split import build_case_report, build_documents_report
    from .contam.story import build_story

    summary = json.loads((RESULTS_DIR / "summary.json").read_text())
    for fn in (build_paper, build_explainer, build_short_report, build_lawyer_guide, build_documents_report, build_case_report, build_story):
        console.print(f"wrote {fn(summary)}")


@app.command("contam-review")
def contam_review():
    """Side-by-side review page for the finish-the-document probe (results/contam/verbatim_review.html)."""
    from .contam.review import build_verbatim_review

    console.print(f"wrote {build_verbatim_review()}")


# ------------------------------------------------------------------------------------------------ pseudonymisation ablation


@app.command("ablation-build")
def ablation_build(veridian_only: bool = typer.Option(False, "--veridian-only", help="regenerate only veridian__renamed.jsonl from the existing sample (renamer fix)")):
    """Sample the ablation arms and write their pseudonymised twins to data/ablation/ (no API calls)."""
    from .ablation.build import build, rebuild_veridian_renamed

    if veridian_only:
        rebuild_veridian_renamed(log=console.print)
    else:
        build(log=console.print)


@app.command("ablation-leak")
def ablation_leak(
    model: list[str] = typer.Option(None, "--model", "-m", help="default: gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol"),
    n: int = typer.Option(200, "--n"),
):
    """Residual-leakage check: show renamed Enron documents to each model and ask which real company they come from."""
    from .ablation.run import LLM_MODELS, leak_check

    asyncio.run(leak_check(model or LLM_MODELS, n=n, log=console.print))


@app.command("ablation-run")
def ablation_run(
    model: list[str] = typer.Option(None, "--model", "-m", help="default: gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol, jev@base"),
    arm: list[str] = typer.Option(None, "--arm", help="enron_j | enron_k | veridian | mnk (default all)"),
    condition: list[str] = typer.Option(None, "--condition", help="named | renamed (default both)"),
    pilot: bool = typer.Option(False, "--pilot", help="50 docs on one topic per Enron arm / first 50 docs elsewhere"),
    topic: list[str] = typer.Option(None, "--topic", help="restrict Enron arms to these topic keys"),
    concurrency: int = typer.Option(None, "--concurrency"),
    project: bool = typer.Option(False, "--project", help="after running, print the projected full-run list cost"),
):
    """Run the paired named/renamed conditions through the benchmark runner (resumable). Models whose API key is not
    set (e.g. jev@base without TYPESAFE_API_KEY) are skipped and reported as pending."""
    from .ablation.build import ARMS
    from .ablation.run import ALL_MODELS, CONDITIONS, projection, run

    res = asyncio.run(run(model or ALL_MODELS, arm or list(ARMS), condition or CONDITIONS, pilot=pilot, topics=topic or None,
                          concurrency=concurrency, log=console.print))
    console.print(json.dumps(res, indent=1))
    if project:
        projection(log=console.print)


@app.command("ablation-report")
def ablation_report():
    """Score the ablation (results/ablation/summary.json, REPORT.md) and render results/ablation/ablation_report.html."""
    from .ablation.report import build_report
    from .ablation.score import score_all

    summary = score_all(log=console.print)
    console.print(f"wrote {build_report(summary)}")


# ------------------------------------------------------------------------------------------------ pseudonymisation ablation, round 2 (CUAD, Jeb Bush)


@app.command("ablation2-build")
def ablation2_build(cost: bool = typer.Option(True, "--cost/--no-cost", help="print the exact cost table after building")):
    """Round 2: sample CUAD (1,200 excerpts) and the Jeb Bush e-mails, write renamed twins, mappings and task yaml to data/ablation/ (no API calls)."""
    from .ablation.round2 import build, cost_table

    build(log=console.print)
    if cost:
        console.print(json.dumps(cost_table(log=console.print), indent=1))


@app.command("ablation2-paraphrase")
def ablation2_paraphrase(
    arm: list[str] = typer.Option(None, "--arm", help="cuad | veridian (default both)"),
    limit: int = typer.Option(None, "--limit", help="pilot: only the first N documents (arm file not written)"),
    judge: bool = typer.Option(True, "--judge/--no-judge", help="after paraphrasing, run the Terra fidelity judge on a sample"),
):
    """Paraphrase the CUAD excerpts and the Veridian control with GPT-5.6 Luna (resumable; deterministic checks; Terra fidelity judge)."""
    from .ablation.round2 import fidelity, paraphrase

    console.print(json.dumps(asyncio.run(paraphrase(tuple(arm) if arm else ("cuad", "veridian"), limit=limit, log=console.print)), indent=1))
    if judge and not limit:
        console.print(json.dumps(asyncio.run(fidelity(log=console.print)), indent=1))


@app.command("ablation2-memo")
def ablation2_memo(
    per_contract: int = typer.Option(2, "--per-contract"),
    limit_contracts: int = typer.Option(None, "--limit-contracts", help="pilot: first N contracts"),
):
    """Finish-the-document probe on every CUAD contract × {original, renamed, paraphrased} × Luna/Terra/Sol → per-contract memorisation dose."""
    from .ablation.round2 import memo

    console.print(json.dumps(asyncio.run(memo(per_contract=per_contract, limit_contracts=limit_contracts, log=console.print))["by_model_variant"], indent=1))


@app.command("ablation2-run")
def ablation2_run(
    model: list[str] = typer.Option(None, "--model", "-m", help="default: gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol, jev@base"),
    arm: list[str] = typer.Option(None, "--arm", help="cuad | veridian | jeb (default all)"),
    condition: list[str] = typer.Option(None, "--condition", help="named | renamed | paraphrased (default: the arm's conditions)"),
    limit: int = typer.Option(None, "--limit", help="smoke test: first N documents, written under a __pilotN tag"),
    concurrency: int = typer.Option(None, "--concurrency"),
):
    """Run the round-2 conditions through the benchmark runner (resumable; stops if realised cost tracks > 25 % over the estimate)."""
    from .ablation.round2 import ARMS2, run
    from .ablation.run import ALL_MODELS

    res = asyncio.run(run(model or ALL_MODELS, arm or list(ARMS2), condition or None, limit=limit, concurrency=concurrency, log=console.print))
    console.print(json.dumps(res, indent=1))


@app.command("ablation2-leak")
def ablation2_leak(
    model: list[str] = typer.Option(None, "--model", "-m", help="default: gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol"),
    n_jeb: int = typer.Option(150, "--n-jeb"),
):
    """Identification check on renamed documents: whose e-mail collection (Jeb) / which real parties (CUAD, one excerpt per contract)."""
    from .ablation.round2 import leak
    from .ablation.run import LLM_MODELS

    console.print(json.dumps(asyncio.run(leak(model or LLM_MODELS, n_jeb=n_jeb, log=console.print)), indent=1))


@app.command("ablation2-report")
def ablation2_report(figures: bool = typer.Option(True, "--figures/--no-figures", help="render the two PNG dot plots via headless Chrome")):
    """Score round 2 (results/ablation/round2/summary.json, REPORT.md) and render the knowledge-effect figures."""
    from .ablation.round2_score import score_all, write_report

    summary = score_all(log=console.print)
    for p in write_report(summary, figures=figures, log=console.print):
        console.print(f"wrote {p}")


# ------------------------------------------------------------------------------------------------ classifier-native contamination tests (Jev)

jev_probe_app = typer.Typer(no_args_is_help=True, help="Classifier-native contamination tests on Jev (design/06_contamination_probe.md): T1 code-name swap, "
                                                        "T2 minimal-edit label flip, T3 paraphrase sensitivity, T4 published vs unpublished labels, bare-token check.")
app.add_typer(jev_probe_app, name="jev-probe")


@jev_probe_app.command("build")
def jev_probe_build(
    no_llm: bool = typer.Option(False, "--no-llm", help="Skip the Luna edit / paraphrase generation (deterministic data only)"),
    scan_edrm: bool = typer.Option(True, "--scan-edrm/--no-scan-edrm", help="Stream EDRM/edrmv2txt-v2.tar.bz2 once for unjudged Enron documents (T4; slow)"),
):
    """Build data/jev_probe/: T1 templated documents, bare-token documents, T2/T3/T4 samples; then Luna edits and paraphrases (resumable, ledgered)."""
    from .jevprobe.build import build, build_t4
    from .jevprobe.edit import make_edits, make_paraphrases
    from .jevprobe.pool import POOL, scan

    build(log=console.print, skip_t4=True)
    if scan_edrm and not POOL.exists():
        scan(log=console.print)
    build_t4(log=console.print)
    if not no_llm:
        async def gen():
            for c in ("enron", "jebbush", "veridian"):
                console.print(await make_edits(c, log=console.print))
            for c in ("enron", "endo", "veridian"):
                console.print(await make_paraphrases(c, log=console.print))
        asyncio.run(gen())


@jev_probe_app.command("run")
def jev_probe_run(
    test: list[str] = typer.Option(["t1", "bt", "t2", "t3", "t4"], "--test", "-t", help="t1 | bt | t2 | t3 | t4"),
    model: Optional[list[str]] = typer.Option(None, "--model", "-m", help="default: jev@base, gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol"),
    cap: float = typer.Option(5.0, "--cap", help="OpenAI spend cap for T1 + T2 (predictions + edit generation), USD"),
    cap_other: float = typer.Option(3.0, "--cap-other", help="OpenAI spend cap for T3 paraphrases + T4 panel, USD"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
):
    """Run the tests on Jev and (under the cap, in priority order) the GPT-5.6 models. Resumable."""
    from .jevprobe.run import run

    console.print(json.dumps(asyncio.run(run(test, model, cap_t12=cap, cap_other=cap_other, concurrency=concurrency, log=console.print))["spend"], indent=1))


@jev_probe_app.command("report")
def jev_probe_report():
    """Score results/jev_probe/ -> summary.json and REPORT.md."""
    from .jevprobe.report import build_report
    from .jevprobe.score import score_all

    build_report(score_all(log=console.print))
    console.print(f"wrote {Path('results/jev_probe/REPORT.md')}")


@app.command("contam-jev")
def contam_jev(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="run only the first N pending items (smoke test)"),
    concurrency: int = typer.Option(8, "--concurrency"),
):
    """Run the M3 header-only relevance probe on Jev -> results/contam/jev.jsonl (resumable)."""
    import asyncio

    from .contam.jev_m3 import run_jev_m3

    console.print(asyncio.run(run_jev_m3(limit=limit, concurrency=concurrency, log=console.print)))


# ---------------------------------------------------------------------------------------------------------------------
# Generalisation checks for the contamination study (ediscovery_bench/verify): A knowledge-dependence tags, B ranking
# stability, C counterfactual conflict documents, D knowledge injection on Veridian. Results under results/verify/.
verify_app = typer.Typer(no_args_is_help=True, help="Generalisation checks for the contamination claim (results/verify/): A knowledge-dependence error analysis, "
                                                   "B ranking stability, C counterfactual conflict documents, D knowledge injection on Veridian.")
app.add_typer(verify_app, name="verify")


@verify_app.command("build")
def verify_build():
    """Write the Check C conflict documents (data/verify/c_<matter>.jsonl), the Check D Veridian subset and brief."""
    from .verify import conflict, inject

    console.print(json.dumps(conflict.build(log=console.print), indent=1))
    console.print(json.dumps(inject.build_subset(log=console.print), indent=1))
    console.print(f"brief -> {inject.write_brief()}")


@verify_app.command("run")
def verify_run(
    check: list[str] = typer.Option(["a", "c", "d"], "--check", "-k", help="a | c | d (B needs no calls)"),
    model: Optional[list[str]] = typer.Option(None, "--model", "-m", help="default: gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol, jev@base"),
    cap: float = typer.Option(15.0, "--cap", help="total NEW OpenAI spend cap across A + C + D (paid/flex USD)"),
    limit_a: Optional[int] = typer.Option(None, "--limit-a", help="tag only the first N untagged Enron J documents (smoke test)"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
):
    """Run the checks that call APIs: Jev first, then the GPT-5.6 models under the cap. Resumable."""
    from .verify.run import run

    console.print(json.dumps(asyncio.run(run(check, model, cap=cap, concurrency=concurrency, limit_a=limit_a, log=console.print))["spend"], indent=1))


@verify_app.command("report")
def verify_report():
    """Score A–D -> results/verify/summary.json, REPORT.md and one figure per check."""
    from .verify.report import build_report

    s = build_report(log=console.print)
    console.print(json.dumps({k: v["verdict"] for k, v in s["readings"].items()}, indent=1))


# ------------------------------------------------------------------------------------------------ Big Thorium (sixth collection)

bt_app = typer.Typer(no_args_is_help=True, help="Big Thorium — Relativity's synthetic aiR demo set as a second floor: extract, sample, rename, run, score, probe.")
app.add_typer(bt_app, name="bigthorium")


@bt_app.command("extract")
def bigthorium_extract():
    """Unpacked ARM archive -> data/bigthorium/bigthorium_all.jsonl, air_criteria.json, human_coding.json."""
    from .bigthorium.extract import build

    console.print(json.dumps(build(log=console.print), indent=1))


@bt_app.command("build")
def bigthorium_build():
    """Stratified 1,000-document sample, renamer mapping, renamed file and residual audit (data/ablation/bigthorium*.jsonl)."""
    from .ablation.bigthorium import build_renamed, build_sample, estimate

    build_sample(log=console.print)
    rep = build_renamed(log=console.print)
    if any(rep["residuals"][k] for k in ("phrase", "rare_surname", "email_local")):
        console.print("[red]residual audit is not zero — fix the mapping before any renamed run[/red]")
    estimate(log=console.print)


@bt_app.command("run")
def bigthorium_run(
    condition: list[str] = typer.Option(["named"], "--condition", "-k", help="named | renamed | brief (goldify after named, before brief)"),
    model: Optional[list[str]] = typer.Option(None, "--model", "-m"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="smoke test on the first N documents"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
):
    """Classification runs through the ordinary runner (resumable; spend recorded in data/ablation/round2_spend.json)."""
    from .ablation.bigthorium import run

    console.print(json.dumps(asyncio.run(run(condition, _expand_models(model) if model else None, limit=limit, concurrency=concurrency, log=console.print)), indent=1))


@bt_app.command("goldify")
def bigthorium_goldify():
    """Panel gold from the three named runs into the sample files; picks the brief subset."""
    from .ablation.bigthorium import goldify

    goldify(log=console.print)


@bt_app.command("score")
def bigthorium_score():
    """results/ablation/bigthorium/{summary.json, REPORT.md} and the pr_options figures."""
    from .ablation.bigthorium import score

    score(log=console.print)


@bt_app.command("probe-build")
def bigthorium_probe_build():
    """Contamination probe items for Big Thorium -> data/contam/bigthorium_probes.jsonl."""
    from .contam.bigthorium import build_items

    build_items(log=console.print)


@bt_app.command("probe-run")
def bigthorium_probe_run(model: Optional[list[str]] = typer.Option(None, "--model", "-m"), concurrency: int = typer.Option(8, "--concurrency")):
    """Run the Big Thorium probe items (resumable; results/contam/<model>.jsonl)."""
    from .contam.bigthorium import MODELS as BT_MODELS, run

    console.print(json.dumps(asyncio.run(run(_expand_models(model) if model else BT_MODELS, concurrency=concurrency, log=console.print)), indent=1))


@bt_app.command("probe-score")
def bigthorium_probe_score():
    """Score the Big Thorium probes -> results/contam/bigthorium_summary.json (read by contam-html / contam-paper)."""
    from .contam.bigthorium import score

    score(log=console.print)

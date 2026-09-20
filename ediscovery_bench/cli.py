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
from .runner import job_path, load_predictions, run_jobs
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
        run_jobs(ts, docs, keys, arm, out, corpus, concurrency=concurrency, effort=effort, phrasing=phrasing, batch=batch, flex=not no_flex, tag=tag)
    )
    _report(ts, out, corpus, arm, keys, tag)


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
):
    """Recompute tables from saved predictions."""
    ts = TaskSet.load(task)
    keys = _expand_models(model) if model else None
    _report(ts, out, corpus, arm, keys, tag, exclude_gray, per_question)


def _fmt(v, pct=False, nd=3):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{v*100:.1f}" if pct else f"{v:.{nd}f}"


def _report(ts, out: Path, corpus: str, arms, keys, tag="", exclude_gray=False, per_question=False):
    pos = ts.positive_label
    found: dict[str, list] = {}
    for a in arms:
        d = out / corpus / a
        if not d.exists():
            continue
        for f in sorted(d.glob("*.jsonl")):
            name = f.stem
            if tag and not name.endswith(f"__{tag}"):
                continue
            if not tag and "__" in name and not name.startswith("jev__"):
                # tagged files (e.g. pilots) are excluded unless asked for
                base = name.split("__")
                if len(base) > 1 and base[0] != "jev":
                    continue
            mk = name.replace("__", "@", 1) if name.startswith("jev__") else name.split("__")[0]
            if keys and mk not in keys:
                continue
            preds = load_predictions(f)
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

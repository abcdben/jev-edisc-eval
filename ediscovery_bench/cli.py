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

from .config import DEFAULT_ROSTER, ENV_KEYS, MODELS, resolve_models
from .metrics import agreement_matrix, summarize
from .providers import make_provider
from .runner import load_predictions, predictions_path, run_task
from .tasks import Task, load_documents

app = typer.Typer(no_args_is_help=True, help="Jev vs LLMs on eDiscovery classification.")
console = Console()

load_dotenv()


@app.command()
def models():
    """List the model roster and pricing."""
    t = Table(title="Model roster (USD per 1M tokens)")
    for c in ["key", "provider", "wire id", "size", "effort", "in $", "out $", "key set?"]:
        t.add_column(c)
    for m in MODELS.values():
        has = "—" if not ENV_KEYS[m.provider] else ("yes" if os.environ.get(ENV_KEYS[m.provider]) else "[red]no[/red]")
        t.add_row(m.key, m.provider, m.model_id, m.size, m.effort or "default", f"{m.input_per_mtok:g}", f"{m.output_per_mtok:g}", has)
    console.print(t)
    console.print(f"Default roster: {', '.join(DEFAULT_ROSTER)}")


@app.command()
def doctor(
    model: Optional[list[str]] = typer.Option(None, "--model", "-m", help="Model keys to check (default: all with a key set)"),
):
    """Check API keys and make ONE tiny classification call per provider.

    This does hit each vendor's API (a few hundred tokens each)."""
    specs = resolve_models(model) if model else [MODELS[k] for k in DEFAULT_ROSTER]

    async def check(spec):
        env = ENV_KEYS[spec.provider]
        if env and not os.environ.get(env):
            return spec.key, f"[yellow]skipped[/yellow]  {env} not set"
        try:
            p = make_provider(spec)
            try:
                return spec.key, "[green]" + await p.healthcheck() + "[/green]"
            finally:
                await p.aclose()
        except Exception as e:  # noqa: BLE001
            return spec.key, f"[red]FAIL[/red]  {type(e).__name__}: {e}"

    async def main():
        return await asyncio.gather(*(check(s) for s in specs))

    for key, status in asyncio.run(main()):
        console.print(f"{key:<18} {status}")


@app.command()
def run(
    task: Path = typer.Option(..., "--task", "-t", help="Task YAML"),
    data: Path = typer.Option(..., "--data", "-d", help="Documents JSONL"),
    model: Optional[list[str]] = typer.Option(None, "--model", "-m", help="Model keys (default: full roster). Use 'mock' for offline."),
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Only the first N documents"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c"),
    effort: Optional[str] = typer.Option(None, "--effort", help="Override LLM effort/thinking level (low|medium|high...)"),
    label_field: Optional[str] = typer.Option(None, "--label-field", help="Gold label field in JSONL (default: task name, then 'label')"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the cost/confirmation prompt"),
):
    """Run one task across models. Resumable; re-run to fill gaps."""
    t = Task.load(task)
    docs = load_documents(data, limit=limit, label_field=label_field or t.name)
    if all(d.label is None for d in docs):
        docs = load_documents(data, limit=limit, label_field="label")
    specs = resolve_models(model)

    n_gold = sum(1 for d in docs if d.label is not None)
    approx_tokens = sum(len(d.text) // 4 + len(t.instructions) // 4 + len(t.context) // 4 + 150 for d in docs)
    console.print(f"[bold]{t.name}[/bold] ({t.kind}) · {len(docs)} docs ({n_gold} with gold) · models: {', '.join(s.key for s in specs)}")
    est = sum(s.cost_usd(approx_tokens, 60 * len(docs)) for s in specs)
    console.print(f"Rough input-side cost estimate: ~${est:.2f} (LLM thinking tokens not included)")
    if not yes and not typer.confirm("Proceed?", default=False):
        raise typer.Exit(1)

    results = asyncio.run(run_task(t, docs, specs, out, concurrency, effort))
    _print_report(t, results, out)


@app.command()
def report(
    task: Path = typer.Option(..., "--task", "-t"),
    out: Path = typer.Option(Path("results"), "--out", "-o"),
    model: Optional[list[str]] = typer.Option(None, "--model", "-m"),
):
    """Recompute the report from saved predictions (no API calls)."""
    t = Task.load(task)
    specs = resolve_models(model) if model else [
        MODELS[k] for k in MODELS if predictions_path(out, t, MODELS[k]).exists()
    ]
    results = {s.key: list(load_predictions(predictions_path(out, t, s)).values()) for s in specs}
    results = {k: v for k, v in results.items() if v}
    if not results:
        console.print("[red]no predictions found[/red]")
        raise typer.Exit(1)
    _print_report(t, results, out)


def _fmt(v, pct=False, nd=3):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{v*100:.1f}%" if pct else f"{v:.{nd}f}"


def _print_report(t: Task, results, out: Path):
    summaries = {k: summarize(t, v) for k, v in results.items()}

    tbl = Table(title=f"{t.name}: classification quality")
    if t.kind == "binary":
        cols = ["model", "n", "err", "prec", "recall", "F1", "elusion", "κ", "ROC AUC", "PR AUC", "Brier", "ECE"]
    else:
        cols = ["model", "n", "err", "acc", "macro F1", "κ", "Brier", "ECE"]
    for c in cols:
        tbl.add_column(c, justify="right" if c != "model" else "left")
    for s in summaries.values():
        if t.kind == "binary":
            tbl.add_row(s.model, str(s.n), str(s.n_errors), _fmt(s.precision, True), _fmt(s.recall, True), _fmt(s.f1, True),
                        _fmt(s.elusion, True), _fmt(s.kappa), _fmt(s.roc_auc), _fmt(s.pr_auc), _fmt(s.brier), _fmt(s.ece))
        else:
            tbl.add_row(s.model, str(s.n), str(s.n_errors), _fmt(s.accuracy, True), _fmt(s.macro_f1, True), _fmt(s.kappa), _fmt(s.brier), _fmt(s.ece))
    console.print(tbl)

    if t.kind == "binary":
        tbl = Table(title=f"{t.name}: threshold on p({t.positive_label}) needed to reach a recall target")
        for c in ["model", "recall≥75% thr / prec / review%", "recall≥90% thr / prec / review%", "recall≥95% thr / prec / review%"]:
            tbl.add_column(c)
        for s in summaries.values():
            row = [s.model]
            for k in ["recall@75", "recall@90", "recall@95"]:
                r = s.recall_targets.get(k)
                row.append("—" if not r else f"{r['threshold']:.2f} / {r['precision']*100:.0f}% / {r['review_fraction']*100:.0f}%")
            tbl.add_row(*row)
        console.print(tbl)

    tbl = Table(title=f"{t.name}: speed and cost")
    for c in ["model", "resolved", "p50 ms", "p95 ms", "in tok", "out tok", "total $", "$ / 1k docs", "× Jev $"]:
        tbl.add_column(c, justify="right" if c not in ("model", "resolved") else "left")
    jev_cost = next((s.cost_per_1k_docs_usd for s in summaries.values() if s.model.startswith("jev")), None)
    for s in summaries.values():
        ratio = "—" if not jev_cost else f"{s.cost_per_1k_docs_usd / jev_cost:,.0f}×"
        tbl.add_row(s.model, s.model_resolved, f"{s.latency_p50_ms:,.0f}", f"{s.latency_p95_ms:,.0f}",
                    f"{s.input_tokens_mean:,.0f}", f"{s.output_tokens_mean:,.0f}", f"${s.total_cost_usd:.4f}",
                    f"${s.cost_per_1k_docs_usd:.4f}", ratio)
    console.print(tbl)

    if len(results) > 1:
        agree = agreement_matrix(t, results)
        tbl = Table(title=f"{t.name}: inter-model agreement (Cohen's κ)")
        tbl.add_column("")
        for k in agree:
            tbl.add_column(k[:12], justify="right")
        for a, row in agree.items():
            tbl.add_row(a, *[_fmt(row[b], nd=2) for b in agree])
        console.print(tbl)

    summary_path = out / t.name / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps({k: s.to_dict() for k, s in summaries.items()}, indent=2))
    console.print(f"[dim]summary → {summary_path}[/dim]")


if __name__ == "__main__":
    app()

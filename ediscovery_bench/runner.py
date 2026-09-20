"""Runs one task across N models, writing one JSONL of predictions per model.

Resumable: existing predictions for a (task, model) are loaded and their
doc_ids skipped, so a crashed or rate-limited run can be re-invoked safely.
Failed predictions (error != None) are re-attempted on resume.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn

from .config import ModelSpec
from .providers import Prediction, make_provider
from .tasks import Document, Task, iter_jsonl

console = Console()

# Per-provider concurrency. Jev's published limit is 1,200 rpm; the LLMs vary
# by account tier. Conservative defaults; override with --concurrency.
DEFAULT_CONCURRENCY = {
    "typesafe": 16,
    "anthropic": 6,
    "openai": 6,
    "gemini": 6,
    "mock": 32,
}


def predictions_path(out_dir: Path, task: Task, spec: ModelSpec) -> Path:
    return out_dir / task.name / f"{spec.key}.jsonl"


def load_predictions(path: Path) -> dict[str, Prediction]:
    out: dict[str, Prediction] = {}
    for row in iter_jsonl(path):
        p = Prediction.from_row(row)
        out[p.doc_id] = p
    return out


async def run_model(
    task: Task,
    docs: list[Document],
    spec: ModelSpec,
    out_dir: Path,
    concurrency: int | None = None,
    effort: str | None = None,
    progress: Progress | None = None,
) -> list[Prediction]:
    path = predictions_path(out_dir, task, spec)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = load_predictions(path)
    done_ok = {d for d, p in existing.items() if not p.error}
    todo = [d for d in docs if d.id not in done_ok]

    provider = make_provider(spec, effort_override=effort)
    sem = asyncio.Semaphore(concurrency or DEFAULT_CONCURRENCY[spec.provider])
    task_id = progress.add_task(f"{spec.key:<18}", total=len(docs), completed=len(done_ok)) if progress else None

    # Rewrite file without stale errored rows, then append as we go.
    with path.open("w") as f:
        for p in existing.values():
            if not p.error:
                f.write(json.dumps(p.to_row()) + "\n")

    lock = asyncio.Lock()

    async def one(doc: Document) -> Prediction:
        async with sem:
            pred = await provider.classify(task, doc)
        async with lock:
            with path.open("a") as f:
                f.write(json.dumps(pred.to_row()) + "\n")
            if progress and task_id is not None:
                progress.advance(task_id)
        return pred

    try:
        new = await asyncio.gather(*(one(d) for d in todo))
    finally:
        await provider.aclose()

    results = {**{d: p for d, p in existing.items() if not p.error}, **{p.doc_id: p for p in new}}
    return [results[d.id] for d in docs if d.id in results]


async def run_task(
    task: Task,
    docs: list[Document],
    specs: list[ModelSpec],
    out_dir: Path,
    concurrency: int | None = None,
    effort: str | None = None,
) -> dict[str, list[Prediction]]:
    results: dict[str, list[Prediction]] = {}
    with Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        coros = [
            run_model(task, docs, spec, out_dir, concurrency, effort, progress) for spec in specs
        ]
        for spec, preds in zip(specs, await asyncio.gather(*coros)):
            results[spec.key] = preds
    return results

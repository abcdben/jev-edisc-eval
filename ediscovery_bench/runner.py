"""Runs a job = (corpus, task set, arm, model key) and writes predictions JSONL.

Layout: results/<corpus>/<arm>/<model_key>.jsonl with one row per (doc, question).
Resumable: rows already present (without error) are skipped.

Arms:
  single: one API call per (document, question)
  multi:  one API call per document covering all questions
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn

from .providers import Prediction, make_provider, parse_model_key
from .tasks import Document, TaskSet, iter_jsonl

console = Console(width=220)

DEFAULT_CONCURRENCY = {"typesafe": 12, "laya": 64, "ollama": 2, "lexical": 64, "anthropic": 8, "openai": 8, "gemini": 8, "mock": 64}


def job_path(out: Path, corpus: str, arm: str, model_key: str, tag: str = "") -> Path:
    name = model_key.replace("@", "__") + (f"__{tag}" if tag else "")
    return out / corpus / arm / f"{name}.jsonl"


VARIANT_FAMILIES = ("jev", "laya", "tar")


def parse_job_stem(stem: str) -> tuple[str, str]:
    """Inverse of job_path: 'jev__choice__pilot' -> ('jev@choice', 'pilot');
    'laya-typed__base' -> ('laya-typed@base', ''); 'gpt-5.6-luna__pilot' -> ('gpt-5.6-luna', 'pilot')."""
    head, _, rest = stem.partition("__")
    if rest and any(head == f or head.startswith(f + "-") for f in VARIANT_FAMILIES):
        variant, _, tag = rest.partition("__")
        return f"{head}@{variant}", tag
    return head, rest


def load_predictions(path: Path) -> list[Prediction]:
    return [Prediction.from_row(r) for r in iter_jsonl(path)]


def _units(docs: list[Document], qids: list[str], arm: str) -> list[tuple[list[str], Document]]:
    if arm == "multi":
        return [(qids, d) for d in docs]
    return [([q], d) for d in docs for q in qids]


async def run_job(
    ts: TaskSet,
    docs: list[Document],
    model_key: str,
    arm: str,
    out: Path,
    corpus: str,
    concurrency: int | None = None,
    effort: str | None = None,
    phrasing: str = "rfp",
    batch: bool = False,
    flex: bool = True,
    temperature: float | None = None,
    tag: str = "",
    progress: Progress | None = None,
    log: Callable[[str], None] = console.print,
) -> list[Prediction]:
    path = job_path(out, corpus, arm, model_key, tag)
    path.parent.mkdir(parents=True, exist_ok=True)
    spec, _ = parse_model_key(model_key)

    existing = load_predictions(path)
    done = {(p.doc_id, p.question) for p in existing if not p.error}
    keep = [p for p in existing if not p.error]
    with path.open("w") as f:
        for p in keep:
            f.write(json.dumps(p.to_row()) + "\n")

    qids = ts.qids
    units = [(qs, d) for qs, d in _units(docs, qids, arm) if any((d.id, q) not in done for q in qs)]
    total = len(docs) * (1 if arm == "multi" else len(qids))
    task_id = progress.add_task(f"{model_key:<24} {arm:<6}", total=total, completed=len(done)) if progress else None

    provider = make_provider(model_key, effort_override=effort, phrasing=phrasing, batch=batch, flex=flex, temperature=temperature)
    lock = asyncio.Lock()
    new: list[Prediction] = []

    async def record(preds: list[Prediction]) -> None:
        async with lock:
            with path.open("a") as f:
                for p in preds:
                    f.write(json.dumps(p.to_row()) + "\n")
            new.extend(preds)
            if progress and task_id is not None:
                progress.advance(task_id, len(preds) if arm == "single" else 1)

    t0 = time.time()
    try:
        if batch and getattr(provider, "supports_batch", False) and units:
            results = await provider.run_batch(ts, units, log=log)  # type: ignore[attr-defined]
            for idx, (qs, d) in enumerate(units):
                r = results.get(idx)
                if isinstance(r, Exception) or r is None:
                    preds = _error_preds(ts, qs, d, model_key, spec.model_id, arm, str(r))
                else:
                    paid, listed = provider.cost(r)
                    n = len(qs)
                    preds = []
                    for q in qs:
                        p = float(min(1.0, max(0.0, r.p_positive.get(q, 0.5))))
                        lab = r.labels.get(q)
                        if lab not in (ts.positive_label, ts.negative_label):
                            lab = ts.positive_label if p >= 0.5 else ts.negative_label
                        preds.append(
                            Prediction(
                                doc_id=d.id, question=q, model_key=model_key, model_resolved=r.resolved_model, arm=arm,
                                label=lab, p_positive=p, confidence=None, latency_ms=None,
                                input_tokens=r.input_tokens // n, output_tokens=r.output_tokens // n,
                                cached_tokens=r.cached_tokens // n, cost_usd=paid / n, list_cost_usd=listed / n,
                                pricing_mode="batch", gold=d.gold(q, ts.negative_label), gray=q in d.gray,
                            )
                        )
                await record(preds)
        else:
            sem = asyncio.Semaphore(concurrency or DEFAULT_CONCURRENCY[spec.provider])

            async def one(qs: list[str], d: Document) -> None:
                async with sem:
                    preds = await provider.classify(ts, qs, d, arm)
                await record(preds)

            await asyncio.gather(*(one(qs, d) for qs, d in units))
    finally:
        await provider.aclose()

    allp = keep + new
    n_err = sum(1 for p in new if p.error)
    paid = sum(p.cost_usd for p in new)
    log(
        f"[dim]{corpus}/{arm}/{model_key}{('#'+tag) if tag else ''}: {len(new)} new rows, {n_err} errors, "
        f"${paid:.3f} paid, {time.time()-t0:.0f}s[/dim]"
    )
    return allp


def _error_preds(ts, qs, d, model_key, model_id, arm, msg) -> list[Prediction]:
    return [
        Prediction(
            doc_id=d.id, question=q, model_key=model_key, model_resolved=model_id, arm=arm, label="",
            p_positive=float("nan"), confidence=None, latency_ms=None, input_tokens=0, output_tokens=0,
            cached_tokens=0, cost_usd=0.0, list_cost_usd=0.0, pricing_mode="batch",
            gold=d.gold(q, ts.negative_label), gray=q in d.gray, error=msg[:500],
        )
        for q in qs
    ]


async def run_jobs(
    ts: TaskSet,
    docs: list[Document],
    model_keys: list[str],
    arms: list[str],
    out: Path,
    corpus: str,
    **kw,
) -> dict[tuple[str, str], list[Prediction]]:
    results: dict[tuple[str, str], list[Prediction]] = {}
    with Progress(
        TextColumn("[bold]{task.description}"), BarColumn(), MofNCompleteColumn(), TimeElapsedColumn(), console=console
    ) as progress:
        coros = [run_job(ts, docs, mk, arm, out, corpus, progress=progress, **kw) for mk in model_keys for arm in arms]
        keys = [(mk, arm) for mk in model_keys for arm in arms]
        for k, preds in zip(keys, await asyncio.gather(*coros)):
            results[k] = preds
    return results

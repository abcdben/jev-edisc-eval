"""Run the probe items against a model. Resumable: results/contam/<model>.jsonl, one row per item."""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path

from ..config import MODELS
from .build import OUT_DIR
from .llm import TextClient

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results" / "contam"

MAX_TOKENS = {"verbatim": 400, "entity_recall": 200, "entity_recog": 16, "bench_knowledge": 1500, "label_recall": 16,  # OpenAI minimum is 16
              "matter_id": 300, "matter_recall": 3000, "evidence_prior": 1200, "metadata_relevance": 16}


def load_items(path: Path = OUT_DIR / "probes.jsonl", probes: list[str] | None = None, corpora: list[str] | None = None, limit: int | None = None) -> list[dict]:
    items = [json.loads(l) for l in path.open()]
    if probes:
        items = [i for i in items if i["probe"] in probes]
    if corpora:
        items = [i for i in items if i["corpus"] in corpora]
    if limit:
        # a few of every (probe, corpus) rather than the first N
        per: Counter = Counter()
        kept = []
        for i in items:
            k = (i["probe"], i["corpus"])
            if per[k] < limit:
                kept.append(i)
                per[k] += 1
        items = kept
    return items


def result_path(model_key: str) -> Path:
    return RESULTS_DIR / f"{model_key}.jsonl"


def load_results(model_key: str) -> dict[str, dict]:
    p = result_path(model_key)
    if not p.exists():
        return {}
    out = {}
    for line in p.open():
        r = json.loads(line)
        if not r.get("error"):
            out[r["item_id"]] = r
    return out


async def run_model(model_key: str, items: list[dict], concurrency: int = 8, log=print) -> dict:
    spec = MODELS[model_key]
    done = load_results(model_key)
    todo = [i for i in items if i["item_id"] not in done]
    log(f"[{model_key}] {len(items)} items, {len(done)} done, {len(todo)} to run")
    if not todo:
        return {"model": model_key, "ran": 0, "cost_usd": 0.0}
    client = TextClient(spec)
    sem = asyncio.Semaphore(concurrency)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_f = result_path(model_key).open("a")
    lock = asyncio.Lock()
    stats = Counter()
    cost = 0.0

    async def one(item: dict):
        nonlocal cost
        async with sem:
            row = {"item_id": item["item_id"], "probe": item["probe"], "corpus": item["corpus"], "model": model_key}
            try:
                c = await client.complete(item["system"], item["user"], MAX_TOKENS.get(item["probe"], 400))
                row.update(
                    response=c.text, input_tokens=c.input_tokens, output_tokens=c.output_tokens, resolved_model=c.resolved_model,
                    latency_s=round(c.latency_s, 3), cost_usd=c.cost_usd, temperature0=c.temperature_applied,
                )
                stats["ok"] += 1
                cost += c.cost_usd
            except Exception as e:  # noqa: BLE001
                row["error"] = f"{type(e).__name__}: {str(e)[:300]}"
                stats["err"] += 1
            async with lock:
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_f.flush()
            n = stats["ok"] + stats["err"]
            if n % 100 == 0 or n == len(todo):
                log(f"[{model_key}] {n}/{len(todo)} ok={stats['ok']} err={stats['err']} ${cost:.3f}")

    try:
        await asyncio.gather(*(one(i) for i in todo))
    finally:
        out_f.close()
        await client.aclose()
    return {"model": model_key, "ran": stats["ok"], "errors": stats["err"], "cost_usd": round(cost, 4)}


async def run_models(model_keys: list[str], items: list[dict], concurrency: int = 8, log=print) -> list[dict]:
    return await asyncio.gather(*(run_model(k, items, concurrency, log) for k in model_keys))

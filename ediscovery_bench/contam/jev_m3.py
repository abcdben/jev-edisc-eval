"""Run the M3 header-only relevance probe on Jev.

Jev is a classifier, not a text generator, so it cannot be posed the other probes; M3 is a relevance call from a fixed set of header
fields and fits its interface directly. Each M3 item in probes.jsonl is turned into one TaskSet (matter context + the request text as
the question, no criteria — the same information the LLM prompt carried) and one Document (the header block under its condition).
Results go to results/contam/jev.jsonl in the same record format as the LLM runs, so score.py picks them up unchanged.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections import Counter

from ..config import MODELS
from ..providers.typesafe import JevConfig, TypeSafeProvider
from ..tasks import Document, Question, TaskSet
from .build import OUT_DIR
from .run import RESULTS_DIR, load_results, result_path

MODEL_KEY = "jev"
PROMPT_RE = re.compile(r"^(?P<ctx>.*?)\n\nRequest — (?P<title>.*?): (?P<rfp>.*?)\n\nE-mail metadata:\n(?P<meta>.*?)\n\nOne word: responsive or not_responsive\.\s*$", re.S)


def _split(item: dict) -> tuple[TaskSet, Document]:
    m = PROMPT_RE.match(item["user"])
    if not m:
        raise ValueError(f"unexpected M3 prompt layout for {item['item_id']}")
    qid = item["meta"]["key"]
    q = Question(id=qid, title=m["title"], rfp_text=m["rfp"], positive_desc="", negative_desc="")
    ts = TaskSet(name=item["meta"]["set"], context=m["ctx"], questions={qid: q})
    return ts, Document(id=item["meta"]["doc_id"], text=m["meta"])


def m3_items() -> list[dict]:
    return [it for it in (json.loads(l) for l in (OUT_DIR / "probes.jsonl").open()) if it["probe"] == "metadata_relevance"]


async def run_jev_m3(limit: int | None = None, concurrency: int = 8, log=print) -> dict:
    items = m3_items()
    done = load_results(MODEL_KEY)
    todo = [i for i in items if i["item_id"] not in done]
    if limit:
        todo = todo[:limit]
    log(f"[{MODEL_KEY}] {len(items)} M3 items, {len(done)} done, {len(todo)} to run")
    if not todo:
        return {"model": MODEL_KEY, "ran": 0, "cost_usd": 0.0}
    prov = TypeSafeProvider(MODELS[MODEL_KEY], cfg=JevConfig(criteria="none"), variant="m3_nocrit")
    sem = asyncio.Semaphore(concurrency)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_f = result_path(MODEL_KEY).open("a")
    lock = asyncio.Lock()
    stats = Counter()
    cost = 0.0

    async def one(item: dict):
        nonlocal cost
        async with sem:
            row = {"item_id": item["item_id"], "probe": item["probe"], "corpus": item["corpus"], "model": MODEL_KEY}
            try:
                ts, doc = _split(item)
                qid = next(iter(ts.questions))
                t0 = time.perf_counter()
                r = await prov._call(ts, [qid], doc)
                p = r.p_positive[qid]
                in_c, out_c = prov.cost(r)
                row.update(response="responsive" if p >= 0.5 else "not_responsive", p_responsive=round(p, 4),
                           input_tokens=r.input_tokens, output_tokens=r.output_tokens, resolved_model=r.resolved_model,
                           latency_s=round(time.perf_counter() - t0, 3), cost_usd=round(in_c + out_c, 6), variant=prov.key)
                stats["ok"] += 1
                cost += in_c + out_c
            except Exception as e:  # noqa: BLE001
                row["error"] = f"{type(e).__name__}: {str(e)[:300]}"
                stats["err"] += 1
            async with lock:
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_f.flush()
            n = stats["ok"] + stats["err"]
            if n % 200 == 0 or n == len(todo):
                log(f"[{MODEL_KEY}] {n}/{len(todo)} ok={stats['ok']} err={stats['err']} ${cost:.4f}")

    try:
        await asyncio.gather(*(one(i) for i in todo))
    finally:
        out_f.close()
        await prov.aclose()
    return {"model": MODEL_KEY, "ran": stats["ok"], "errors": stats["err"], "cost_usd": round(cost, 4)}

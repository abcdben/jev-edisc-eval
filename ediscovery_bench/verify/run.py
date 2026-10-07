"""Run the checks that call APIs (A tagging, C predictions, D predictions) under one OpenAI spend cap; B is free and scored in report.

Order: Jev everywhere first (own key, cheap), then the OpenAI models cheapest-first; every OpenAI job is projected before it runs
and skipped if it would push total new spend over the cap. Everything is resumable.
"""
from __future__ import annotations

import os

from ..config import ENV_KEYS, MODELS
from ..providers import parse_model_key
from ..runner import job_path, load_predictions, run_job
from ..tasks import Document
from . import conflict, inject, knowdep
from .common import CAP_USD, DATA, JEV, LUNA, RESULTS, SOL, SYSTEMS, TERRA, openai_spend, read_jsonl

FLEX = 0.5


def key_available(model_key: str) -> bool:
    spec, _ = parse_model_key(model_key)
    env = ENV_KEYS.get(spec.provider, "")
    return (not env) or bool(os.environ.get(env))


def _docs(rows: list[dict]) -> list[Document]:
    return [Document(id=r["id"], text=r["text"], labels=r.get("labels") or {}, gray=frozenset(r.get("gray") or []), meta=r.get("meta") or {}) for r in rows]


def _estimate(ts, docs, model: str) -> float:
    spec = MODELS[model.split("@")[0]]
    prefix = len(ts.context) + sum(len(q.rfp_text) + len(q.positive_desc) + len(q.negative_desc) + 120 for q in ts.questions.values()) + 400
    in_tok = sum((prefix + len(d.text)) / 4 for d in docs)
    out_tok = len(docs) * (25 + 30 * len(ts.qids))
    return spec.cost_usd(int(in_tok), int(out_tok)) * (FLEX if spec.provider == "openai" else 1.0)


def remaining(cap: float) -> float:
    return cap - openai_spend()["total"]


async def run_c(models: list[str], cap: float, concurrency, log) -> dict:
    out = {}
    for matter in conflict.MATTER_SCENARIOS:
        rows = read_jsonl(DATA / f"c_{matter}.jsonl")
        if not rows:
            log(f"C {matter}: no documents (run build)")
            continue
        ts = conflict.taskset(matter)
        docs = _docs(rows)
        for m in models:
            path = job_path(RESULTS, "c", "multi", m, matter)
            before = {(p.doc_id, p.question) for p in load_predictions(path) if not p.error}
            pending = [d for d in docs if any((d.id, q) not in before for q in ts.qids)]
            if not pending:
                out[f"{m}/{matter}"] = {"new": 0}
                continue
            if not key_available(m):
                log(f"  [pending] {m}: key not set — C/{matter} skipped")
                out[f"{m}/{matter}"] = {"pending": True}
                continue
            spec = MODELS[m.split("@")[0]]
            if spec.provider == "openai":
                est = _estimate(ts, pending, m)
                if est > remaining(cap):
                    log(f"  [budget] C {m}/{matter}: est ${est:.2f} > remaining ${remaining(cap):.2f} — skipped")
                    out[f"{m}/{matter}"] = {"skipped_budget": True, "est": est}
                    continue
            preds = await run_job(ts, docs, m, "multi", RESULTS, "c", concurrency=concurrency, tag=matter, log=log)
            new = [p for p in preds if (p.doc_id, p.question) not in before and not p.error]
            out[f"{m}/{matter}"] = {"new": len(new), "paid": round(sum(p.cost_usd for p in new), 4), "errors": sum(1 for p in preds if p.error)}
    return out


async def run(checks: list[str], models: list[str] | None = None, cap: float = CAP_USD, concurrency: int | None = None, limit_a: int | None = None, log=print) -> dict:
    models = models or SYSTEMS
    res: dict = {}
    log(f"verify run: checks={checks} models={models} cap=${cap:.2f} (spent so far ${openai_spend()['total']:.2f})")
    if "a" in checks:
        if os.environ.get(ENV_KEYS["openai"]):
            res["a"] = await knowdep.tag(limit=limit_a, log=log) if remaining(cap) > 0.5 else {"skipped_budget": True}
        else:
            log("A: OPENAI_API_KEY not set — skipped")
    order = [JEV] + [m for m in (LUNA, TERRA, SOL) if m in models]
    order = [m for m in order if m in models]
    if "c" in checks:
        res["c"] = await run_c(order, cap, concurrency, log)
    if "d" in checks:
        # Jev first (own key), then the OpenAI models cheapest-first under the remaining cap
        res["d"] = {}
        for m in order:
            if not key_available(m):
                log(f"  [pending] {m}: key not set — D skipped")
                res["d"][m] = {"pending": True}
                continue
            r = await inject.run([m], remaining_cap=remaining(cap), concurrency=concurrency, log=log)
            res["d"][m] = r.get(m, {})
            res["d"]["estimate"] = r.get("estimate")
    res["spend"] = openai_spend()
    log(f"spend: {res['spend']}")
    return res

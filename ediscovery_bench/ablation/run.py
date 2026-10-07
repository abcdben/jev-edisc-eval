"""Run the ablation arms through the ordinary benchmark runner.

Result files:  results/ablation/<arm>/multi/<model>__<condition>__<topic>.jsonl   (Enron: one file per judged topic)
               results/ablation/<arm>/multi/<model>__<condition>__all.jsonl       (Veridian, Mallinckrodt: all requests per call)
Conditions:    named   = original documents + context naming the real company (Enron) / original context (Veridian) /
                         no brief (Mallinckrodt)
               renamed = pseudonymised documents + pseudonymised context          (Enron, Veridian)
                         original documents + a one-page case brief in the context (Mallinckrodt; the "treated" slot)

Jev (`jev@base`) goes through exactly the same code path. If TYPESAFE_API_KEY is not set the Jev jobs are skipped and
recorded as pending; they resume where they left off once the key is present.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

from ..config import ENV_KEYS, MODELS
from ..providers import parse_model_key
from ..runner import job_path, load_predictions, run_job
from ..tasks import Document, TaskSet
from .build import ARMS, DATA, ROOT, arm_tasksets, load_renamers

RESULTS = ROOT / "results" / "ablation"
LLM_MODELS = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]
JEV = "jev@base"
ALL_MODELS = LLM_MODELS + [JEV]
CONDITIONS = ("named", "renamed")
PILOT_TOPICS = {"enron_j": ["prepay_transactions"], "enron_k": ["oil_gas_drilling"]}
PILOT_N = 50  # per topic, both conditions


def key_available(model_key: str) -> bool:
    spec, _ = parse_model_key(model_key)
    env = ENV_KEYS.get(spec.provider, "")
    return (not env) or bool(os.environ.get(env))


def _docs(path: Path) -> list[Document]:
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out.append(Document(id=r["id"], text=r["text"], labels=r.get("labels") or {}, gray=frozenset(r.get("gray") or []), meta=r.get("meta") or {}))
    return out


def arm_docs(arm: str, condition: str) -> list[Document]:
    if arm == "mnk" or condition == "named":
        return _docs(DATA / f"{arm}.jsonl")
    return _docs(DATA / f"{arm}__renamed.jsonl")


def jobs(arm: str, condition: str, pilot: bool = False, topics: list[str] | None = None) -> list[tuple[TaskSet, list[Document], str]]:
    """(taskset, docs, tag) units for one arm × condition."""
    rn_e, rn_v = load_renamers()
    ts = arm_tasksets(arm, rn_e if arm.startswith("enron") else rn_v if arm == "veridian" else None)[condition]
    docs = arm_docs(arm, condition)
    if ARMS[arm]["per_doc_topic"]:
        by: dict[str, list[Document]] = defaultdict(list)
        for d in docs:
            by[d.meta["topic_key"]].append(d)
        want = topics or (PILOT_TOPICS[arm] if pilot else ARMS[arm]["topics"])
        out = []
        for t in want:
            ds = by[t]
            if pilot:
                ds = _pilot_subset(ds, t)
            out.append((ts.subset([t]), ds, f"{condition}__{t}"))
        return out
    if pilot:
        docs = sorted(docs, key=lambda d: d.id)[:PILOT_N]
    return [(ts, docs, f"{condition}__all")]


def _pilot_subset(ds: list[Document], topic: str) -> list[Document]:
    """Deterministic balanced subset of PILOT_N docs — the same ids in both conditions (same doc ids)."""
    pos = sorted((d for d in ds if d.labels.get(topic) == "responsive"), key=lambda d: d.id)
    neg = sorted((d for d in ds if d.labels.get(topic) != "responsive"), key=lambda d: d.id)
    return pos[: PILOT_N // 2] + neg[: PILOT_N - PILOT_N // 2]


async def run(models: list[str], arms: list[str], conditions=CONDITIONS, pilot: bool = False, topics: list[str] | None = None,
              concurrency: int | None = None, log=print) -> dict:
    """Returns {"spent": {model: paid}, "list": {model: list}, "pending": [models without a key], "rows": n}."""
    spent: Counter = Counter()
    listed: Counter = Counter()
    pending = [m for m in models if not key_available(m)]
    for m in pending:
        spec, _ = parse_model_key(m)
        log(f"[pending] {m}: {ENV_KEYS[spec.provider]} not set — skipped; re-run the same command once it is present")
    live = [m for m in models if key_available(m)]
    n_rows = 0
    t0 = time.time()
    for arm in arms:
        for cond in conditions:
            for ts, docs, tag in jobs(arm, cond, pilot=pilot, topics=topics):
                for m in live:
                    before = {(p.doc_id, p.question) for p in load_predictions(job_path(RESULTS, arm, "multi", m, tag)) if not p.error}
                    preds = await run_job(ts, docs, m, "multi", RESULTS, arm, concurrency=concurrency, tag=tag, log=log)
                    new = [p for p in preds if (p.doc_id, p.question) not in before and not p.error]
                    spent[m] += sum(p.cost_usd for p in new)
                    listed[m] += sum(p.list_cost_usd for p in new)
                    n_rows += len(new)
    log(f"ablation run: {n_rows} new rows in {time.time()-t0:.0f}s; paid ${sum(spent.values()):.2f} (list ${sum(listed.values()):.2f})")
    return {"spent": dict(spent), "list": dict(listed), "pending": pending, "rows": n_rows}


# ------------------------------------------------------------------------------------------------ cost projection

def _tag_of(stem: str, model_key: str) -> str:
    return stem[len(model_key.replace("@", "__")) + 2:]


def projection(models: list[str] = LLM_MODELS, log=print) -> dict:
    """Project the full-run list cost per model from observed rows: list cost per (document + prompt) character,
    applied to the planned calls of every arm × condition."""
    plan: dict[tuple[str, str], tuple[int, float, int]] = {}  # (arm, tag) -> (n_docs, mean chars per call, n_questions)
    for arm in ARMS:
        for cond in CONDITIONS:
            for ts, docs, tag in jobs(arm, cond):
                prompt = len(ts.context) + sum(len(q.rfp_text) + len(q.positive_desc) + len(q.negative_desc) for q in ts.questions.values())
                plan[(arm, tag)] = (len(docs), prompt + sum(len(d.text) for d in docs) / max(1, len(docs)), len(ts.qids))
    out = {}
    for m in models:
        cost, chars, nrows, calls = 0.0, 0.0, 0, 0
        for f in RESULTS.glob(f"*/multi/{m.replace('@', '__')}__*.jsonl"):
            arm, tag = f.parts[-3], _tag_of(f.stem, m)
            if (arm, tag) not in plan:
                continue
            ps = [p for p in load_predictions(f) if not p.error]
            n_docs, mean_chars, nq = plan[(arm, tag)]
            cost += sum(p.list_cost_usd for p in ps)
            chars += len(ps) / nq * mean_chars
            calls += len(ps) // nq
            nrows += len(ps)
        if not calls:
            out[m] = {"observed_rows": 0}
            log(f"{m}: no rows observed")
            continue
        rate = cost / chars
        total = sum(n * mc for n, mc, _ in plan.values()) * rate
        out[m] = {"observed_rows": nrows, "observed_calls": calls, "observed_list": round(cost, 2), "list_per_call": round(cost / calls, 4),
                  "projected_full_list": round(total, 1), "planned_calls": sum(n for n, _, _ in plan.values())}
        log(f"{m}: {calls} calls observed (${cost:.2f} list, ${cost/calls:.4f}/call); projected full run ≈ ${total:.0f} list")
    out["_planned_calls"] = {f"{a}/{t}": n for (a, t), (n, _, _) in plan.items()}
    return out


# ------------------------------------------------------------------------------------------------ residual-leakage check (M0 on renamed docs)

LEAK_SYSTEM = ("You are a litigation analyst. You will be shown a document from a litigation production in which the names "
               "have been changed. Say which real-world company or matter the document most likely comes from, and why. If you "
               "cannot tell, say so.")
LEAK_USER = ("{doc}\n\nWhich real company's files does this document come from? Name the company first (one name, or "
             "\"cannot tell\"), then give your reasons in two or three sentences.")
LEAK_N = 200


async def leak_check(models: list[str] = LLM_MODELS, n: int = LEAK_N, log=print) -> dict:
    """Show n renamed Enron-J documents to each model and ask which real company they come from."""
    from ..contam.llm import TextClient

    rows = [json.loads(l) for l in (DATA / "enron_j__renamed.jsonl").read_text().splitlines() if l.strip()]
    rng = random.Random(7)
    rng.shuffle(rows)
    # over-sample high-dose docs so the check is conservative: half from dose 3+, half uniform
    hi = [r for r in rows if r["meta"]["dose"] >= 3][: n // 2]
    rest = [r for r in rows if r not in hi][: n - len(hi)]
    sample = hi + rest
    out_path = RESULTS / "leak_check.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["model"], r["doc_id"]) for r in (json.loads(l) for l in out_path.read_text().splitlines() if l.strip())} if out_path.exists() else set()
    sem = asyncio.Semaphore(8)
    cost = 0.0

    async def one(m: str, client, r: dict):
        nonlocal cost
        if (m, r["id"]) in done:
            return
        async with sem:
            c = await client.complete(LEAK_SYSTEM, LEAK_USER.format(doc=r["text"][:12000]), max_tokens=160)
        cost += c.cost_usd
        rec = {"model": m, "doc_id": r["id"], "dose": r["meta"]["dose"], "topic": r["meta"].get("topic_key"), "answer": c.text, "cost_usd": c.cost_usd}
        with out_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")

    for m in models:
        if not key_available(m):
            log(f"[pending] {m}: key not set — leak check skipped")
            continue
        spec, _ = parse_model_key(m)
        client = TextClient(spec)
        await asyncio.gather(*(one(m, client, r) for r in sample))
    recs = [json.loads(l) for l in out_path.read_text().splitlines() if l.strip()]
    summ = score_leak(recs)
    log(f"leak check: {len(recs)} answers, ${cost:.2f}; " + ", ".join(f"{m}: {v['named_enron']}/{v['n']} name Enron" for m, v in summ.items()))
    return summ


def score_leak(recs: list[dict]) -> dict:
    out: dict = {}
    for m in sorted({r["model"] for r in recs}):
        rs = [r for r in recs if r["model"] == m]
        enron = [r for r in rs if "enron" in r["answer"].lower()]
        by_dose = {}
        for band, lo, hi in (("0", 0, 0), ("1-2", 1, 2), ("3+", 3, 10**9)):
            b = [r for r in rs if lo <= r["dose"] <= hi]
            by_dose[band] = {"n": len(b), "named_enron": sum(1 for r in b if "enron" in r["answer"].lower())}
        cannot = sum(1 for r in rs if "cannot tell" in r["answer"].lower()[:80])
        guesses = Counter()
        for r in rs:
            first = r["answer"].strip().split("\n")[0][:60]
            guesses[first.split(".")[0].split(" (")[0].strip("* ")] += 1
        out[m] = {"n": len(rs), "named_enron": len(enron), "cannot_tell": cannot, "by_dose": by_dose, "top_guesses": guesses.most_common(6),
                  "examples_enron": [r["answer"][:300] for r in enron[:3]]}
    return out

"""Check A — knowledge-dependence error analysis on Enron J (no new classification calls).

GPT-5.6 Luna reads each of the 994 ablation Enron J documents with its judged request and says whether the relevance call
needs outside knowledge of the Enron matter (who Fastow is, what Raptor / LJM2 are, what "prepay" meant at Enron, which
banks' analysts covered it …) or is self-contained from the text plus the request. Temperature 0, cached by document.

Then, per system, the ablation's existing named / renamed predictions are split by tag: accuracy and F1 on each subset in
the named condition, the named → renamed change on each subset (cluster bootstrap by document; one judged request per
document, so a document is a pair), and the difference-in-differences Δ(knowledge-dependent) − Δ(self-contained).

Prediction if matter knowledge helps: higher accuracy on knowledge-dependent documents in the named condition AND a larger
drop on them when renamed.
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter, defaultdict

import numpy as np

from ..config import MODELS
from ..runner import load_predictions
from ..tasks import TaskSet
from .common import (DATA, LUNA, POS, RESULTS, ROOT, SEED, SYSTEMS, append_jsonl, boot_delta_by_cluster, indep_diff, ledger_add,
                     prf, read_jsonl, wilson)

ABL = ROOT / "results" / "ablation" / "enron_j" / "multi"
ENRON_J = ROOT / "data" / "ablation" / "enron_j.jsonl"
TAGS = RESULTS / "a_tags.jsonl"
PROMPT_VERSION = "a1"
KNOWLEDGE_TOPICS = ["prepay_transactions", "fas140", "financial_forecasts", "document_destruction", "energy_schedules", "financial_analysts"]
CONTROL_TOPIC = "fantasy_football"
TAG_KD, TAG_SC = "knowledge_dependent", "self_contained"

SYSTEM = (
    "You are a senior eDiscovery reviewer and an expert on the Enron matter (the 2001 accounting scandal: Fastow's LJM partnerships, "
    "the Raptor / Talon / Chewco / Whitewing / JEDI special-purpose entities, the Mahonia and Yosemite prepay financings with Chase and "
    "Citigroup, Arthur Andersen's shredding, the California trading schemes, the analyst relations). You are NOT deciding relevance. "
    "You are classifying what KIND of reading the relevance decision requires."
)
USER = """Request for production (the only thing the reviewer is told about what is sought):
<request>
{request}
</request>

Document:
<document>
{doc}
</document>

Question: to decide correctly whether this document is responsive to the request, does a reviewer need OUTSIDE KNOWLEDGE of the Enron
matter — facts that are neither stated in the document nor in the request (for example: that Raptor, LJM2 or Chewco were off-balance-sheet
vehicles; who Andrew Fastow or Ben Glisan were; that a "prepay" with Mahonia was a disguised loan; that Merrill, Salomon or CSFB were the
analysts covering the company; what the "Andersen" references mean) — or is the decision SELF-CONTAINED: the document's own words plus the
request's words are enough, so a careful reviewer who had never heard of Enron would reach the same call?

Answer with exactly one line of JSON: {{"tag": "knowledge_dependent" | "self_contained", "reason": "<at most 10 words>"}}"""


def _request_text(ts: TaskSet, qid: str) -> str:
    q = ts.questions[qid]
    return f"{q.rfp_text}\nResponsive means: {q.positive_desc}\nNot responsive means: {q.negative_desc}"


def _parse(text: str) -> tuple[str, str]:
    t = text.strip()
    if "{" in t:
        t = t[t.index("{"): t.rindex("}") + 1] if "}" in t else t[t.index("{"):]
    try:
        o = json.loads(t)
        tag = str(o.get("tag", "")).strip().lower()
        reason = str(o.get("reason", ""))[:120]
    except Exception:  # noqa: BLE001
        low = t.lower()
        tag = TAG_KD if "knowledge_dependent" in low else TAG_SC if "self_contained" in low else ""
        reason = t[:120]
    if tag not in (TAG_KD, TAG_SC):
        tag = ""
    return tag, reason


async def tag(limit: int | None = None, concurrency: int = 8, log=print) -> dict:
    """Tag every Enron J document (cached in results/verify/a_tags.jsonl). Returns spend and tag counts."""
    from ..contam.llm import TextClient

    ts = TaskSet.load(ROOT / "tasks" / "enron_j.yaml")
    rows = read_jsonl(ENRON_J)
    done = {r["doc_id"] for r in read_jsonl(TAGS) if r.get("prompt_version") == PROMPT_VERSION and r.get("tag")}
    todo = [r for r in rows if r["id"] not in done]
    if limit:
        todo = todo[:limit]
    log(f"Check A: {len(rows)} documents, {len(done)} tagged, {len(todo)} to tag with {LUNA}")
    if not todo:
        return {"new": 0, "cost_usd": 0.0, **_tag_counts()}
    client = TextClient(MODELS[LUNA])
    sem = asyncio.Semaphore(concurrency)
    cost = 0.0
    n_bad = 0
    lock = asyncio.Lock()

    async def one(r):
        nonlocal cost, n_bad
        qid = r["meta"]["topic_key"]
        user = USER.format(request=_request_text(ts, qid), doc=r["text"][:12000])
        async with sem:
            try:
                c = await client.complete(SYSTEM, user, max_tokens=80)
            except Exception as e:  # noqa: BLE001
                log(f"  [error] {r['id']}: {type(e).__name__}: {str(e)[:120]}")
                return
        t, reason = _parse(c.text)
        async with lock:
            cost += c.cost_usd
            if not t:
                n_bad += 1
            append_jsonl(TAGS, {"doc_id": r["id"], "topic": qid, "gold": r["labels"].get(qid), "tag": t, "reason": reason, "raw": c.text[:200],
                                "prompt_version": PROMPT_VERSION, "model": c.resolved_model, "cost_usd": c.cost_usd,
                                "input_tokens": c.input_tokens, "output_tokens": c.output_tokens, "temperature_applied": c.temperature_applied})

    try:
        await asyncio.gather(*(one(r) for r in todo))
    finally:
        await client.aclose()
    ledger_add("a_tag", LUNA, cost, n_calls=len(todo), note=f"Check A knowledge-dependence tags, prompt {PROMPT_VERSION}")
    log(f"Check A: tagged {len(todo)} ({n_bad} unparsable), ${cost:.3f}")
    return {"new": len(todo), "unparsable": n_bad, "cost_usd": round(cost, 4), **_tag_counts()}


def _tag_counts() -> dict:
    c = Counter(r["tag"] for r in read_jsonl(TAGS) if r.get("prompt_version") == PROMPT_VERSION)
    return {"tags": dict(c)}


def load_tags() -> dict[str, dict]:
    out = {}
    for r in read_jsonl(TAGS):
        if r.get("prompt_version") == PROMPT_VERSION and r.get("tag"):
            out[r["doc_id"]] = r
    return out


# ------------------------------------------------------------------------------------------------ scoring

def _preds(model: str, cond: str) -> dict[str, dict]:
    """doc_id -> prediction row for the document's judged topic (one per document in the Enron J arm)."""
    out = {}
    stem = model.replace("@", "__")
    for f in ABL.glob(f"{stem}__{cond}__*.jsonl"):
        for p in load_predictions(f):
            if p.error or p.gold is None or not p.label:
                continue
            out[p.doc_id] = {"pred": 1 if p.label == POS else 0, "gold": 1 if p.gold == POS else 0, "topic": p.question, "p": p.p_positive}
    return out


def _subset_block(gold, a, b, ids, nb=2000) -> dict:
    """named metrics, renamed metrics, Δ(renamed − named) with CI, accuracy Wilson CI in the named condition."""
    named, renamed = prf(gold, a), prf(gold, b)
    delta, samples = boot_delta_by_cluster(gold, a, b, ids, nb=nb)
    k = int((a == gold).sum())
    named["accuracy_ci"] = list(wilson(k, len(gold)))
    return {"n": int(len(gold)), "pos": int(gold.sum()), "named": named, "renamed": renamed, "delta": delta,
            "right_to_wrong": int(((a == gold) & (b != gold)).sum()), "wrong_to_right": int(((a != gold) & (b == gold)).sum())}, samples


def _acc_diff(ga, pa, gb, pb, nb=2000, seed=SEED) -> dict:
    """accuracy(a subset) − accuracy(b subset), independent bootstrap over documents."""
    rng = np.random.default_rng(seed)
    ca, cb = (pa == ga).astype(float), (pb == gb).astype(float)
    if not len(ca) or not len(cb):
        return {"delta": None, "lo": None, "hi": None}
    bs = [rng.choice(ca, len(ca)).mean() - rng.choice(cb, len(cb)).mean() for _ in range(nb)]
    return {"delta": float(ca.mean() - cb.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5))}


def _f1_diff(ga, pa, gb, pb, nb=2000, seed=SEED) -> dict:
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):
        ia = rng.integers(0, len(ga), len(ga)); ib = rng.integers(0, len(gb), len(gb))
        fa, fb = prf(ga[ia], pa[ia])["f1"], prf(gb[ib], pb[ib])["f1"]
        if fa == fa and fb == fb:
            bs.append(fa - fb)
    fa, fb = prf(ga, pa)["f1"], prf(gb, pb)["f1"]
    return {"delta": fa - fb if fa == fa and fb == fb else None, "lo": float(np.percentile(bs, 2.5)) if bs else None,
            "hi": float(np.percentile(bs, 97.5)) if bs else None}


def score(log=print) -> dict:
    tags = load_tags()
    rows = {r["id"]: r for r in read_jsonl(ENRON_J)}
    out: dict = {"n_docs": len(rows), "n_tagged": len(tags), "prompt_version": PROMPT_VERSION, "tagger": LUNA}
    if not tags:
        out["status"] = "no tags yet"
        return out
    # share knowledge-dependent per request and per gold label
    by_req: dict[str, list] = defaultdict(list)
    by_gold: dict[str, list] = defaultdict(list)
    for d, t in tags.items():
        r = rows.get(d)
        if not r:
            continue
        q = r["meta"]["topic_key"]
        kd = t["tag"] == TAG_KD
        by_req[q].append(kd)
        by_gold["responsive" if r["labels"].get(q) == POS else "not_responsive"].append(kd)
        by_gold[f"{q}/{'pos' if r['labels'].get(q) == POS else 'neg'}"].append(kd)
    out["share_kd_by_request"] = {q: {"n": len(v), "k": sum(v), "share": sum(v) / len(v), "ci": list(wilson(sum(v), len(v)))} for q, v in sorted(by_req.items())}
    out["share_kd_by_gold"] = {g: {"n": len(v), "k": sum(v), "share": sum(v) / len(v)} for g, v in sorted(by_gold.items())}
    allk = [t["tag"] == TAG_KD for d, t in tags.items() if d in rows and rows[d]["meta"]["topic_key"] != CONTROL_TOPIC]
    out["share_kd_overall_knowledge_topics"] = {"n": len(allk), "k": sum(allk), "share": sum(allk) / len(allk) if allk else None, "ci": list(wilson(sum(allk), len(allk)))}
    # reasons: most common words (for the report)
    reasons = Counter()
    for t in tags.values():
        if t["tag"] == TAG_KD:
            reasons[t["reason"].strip().rstrip(".").lower()] += 1
    out["top_kd_reasons"] = reasons.most_common(12)
    # per system
    out["systems"] = {}
    for m in SYSTEMS:
        A, B = _preds(m, "named"), _preds(m, "renamed")
        keys = sorted(k for k in set(A) & set(B) if k in tags and A[k]["topic"] != CONTROL_TOPIC)
        if not keys:
            out["systems"][m] = {"status": "missing"}
            continue
        gold = np.array([A[k]["gold"] for k in keys]); a = np.array([A[k]["pred"] for k in keys]); b = np.array([B[k]["pred"] for k in keys])
        kd = np.array([tags[k]["tag"] == TAG_KD for k in keys])
        ids = keys
        blocks, samples = {}, {}
        for name, mask in (("knowledge_dependent", kd), ("self_contained", ~kd), ("all", np.ones(len(keys), bool))):
            idx = np.where(mask)[0]
            if len(idx) < 5:
                continue
            blocks[name], samples[name] = _subset_block(gold[idx], a[idx], b[idx], [ids[i] for i in idx])
        res = {"status": "ok", "n": len(keys), "n_kd": int(kd.sum()), "n_sc": int((~kd).sum()), "subsets": blocks}
        if "knowledge_dependent" in blocks and "self_contained" in blocks:
            i_kd, i_sc = np.where(kd)[0], np.where(~kd)[0]
            res["named_acc_kd_minus_sc"] = _acc_diff(gold[i_kd], a[i_kd], gold[i_sc], a[i_sc])
            res["named_f1_kd_minus_sc"] = _f1_diff(gold[i_kd], a[i_kd], gold[i_sc], a[i_sc])
            res["delta_kd_minus_delta_sc"] = indep_diff(samples["knowledge_dependent"], samples["self_contained"],
                                                        blocks["knowledge_dependent"]["delta"], blocks["self_contained"]["delta"])
        # per request × tag named accuracy (small cells, point estimates only)
        per_req = {}
        for q in KNOWLEDGE_TOPICS:
            qi = np.array([A[k]["topic"] == q for k in keys])
            cell = {}
            for name, mask in (("kd", kd & qi), ("sc", ~kd & qi)):
                idx = np.where(mask)[0]
                if len(idx):
                    cell[name] = {"n": int(len(idx)), "acc_named": float((a[idx] == gold[idx]).mean()), "acc_renamed": float((b[idx] == gold[idx]).mean())}
            per_req[q] = cell
        res["per_request"] = per_req
        out["systems"][m] = res
        kdb, scb = blocks.get("knowledge_dependent"), blocks.get("self_contained")
        if kdb and scb:
            log(f"A {m:14s} KD n={kdb['n']:3d} acc {kdb['named']['accuracy']:.3f} F1 {kdb['named']['f1']:.3f} ΔF1 {100*kdb['delta']['f1']['delta']:+.1f}  |  "
                f"SC n={scb['n']:3d} acc {scb['named']['accuracy']:.3f} F1 {scb['named']['f1']:.3f} ΔF1 {100*scb['delta']['f1']['delta']:+.1f}")
    return out

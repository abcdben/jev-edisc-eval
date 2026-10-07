"""LLM-generated twins: T2 minimal label-flipping edits and T3 meaning-preserving paraphrases (GPT-5.6 Luna, temperature 0).

Resumable: ids already present in the output file are skipped. Every call is written to the spend ledger.
  data/jev_probe/t2_<coll>__edited.jsonl   edited twin; labels carry the NEW (flipped) label; meta.old_label, meta.edits, meta.feasible
  data/jev_probe/t3_<corpus>__para.jsonl   paraphrased twin; meta.similarity = difflib ratio to the original body
"""
from __future__ import annotations

import asyncio
import difflib
import json
import re

from ..config import MODELS
from ..contam.llm import TextClient
from ..tasks import TaskSet
from .common import DATA, LUNA, ROOT, append_jsonl, ledger_add, read_jsonl

T2_TASKS = {"enron": "tasks/enron_j.yaml", "jebbush": "tasks/trec.yaml", "veridian": "tasks/veridian.yaml"}
T3_TASKS = {"enron": "tasks/enron_j.yaml", "endo": "tasks/endo.yaml", "veridian": "tasks/veridian.yaml"}

EDIT_SYSTEM = (
    "You edit documents for a controlled experiment on relevance classifiers. You make the smallest possible change to a "
    "document so that its TRUE relevance to a request flips, and you report the change as exact find/replace operations. "
    "You never explain outside the JSON."
)
EDIT_USER = """Request "{title}":
{rfp}

Responsive means: {pos}
Not responsive means: {neg}

Current status: a human assessor judged this document {status} to the request.
Goal: make it {goal}, with the smallest edit that a careful reviewer applying the criteria above would accept.

Rules:
- At most 2 operations. Each "old" must be an exact, verbatim, contiguous substring of the document that appears exactly once (copy it character for character, including line breaks and punctuation), at most 400 characters long.
- To make the document NOT responsive: replace the sentence(s) that carry the responsive content with sentences of similar length on an unrelated everyday business matter, keeping the tone, the people, and the formatting. If the Subject line alone makes it responsive you may change the Subject line.
- To make the document responsive: change one or two sentences so that the document now clearly concerns the request as defined by "responsive means" (you may replace a sentence with itself followed by one new sentence). Keep it in character for the sender.
- Do not touch anything else. Do not add a signature, a note, or a comment.
- If the flip cannot be achieved within 2 operations (for example because the whole document is about the request), set "feasible" to false and give no edits.

Output JSON only: {{"feasible": true|false, "edits": [{{"old": "...", "new": "..."}}], "note": "<= 20 words"}}

Document:
<<<
{doc}
>>>"""

PARA_SYSTEM = (
    "You rewrite documents for a controlled experiment. Your rewrite must state exactly the same facts, names, numbers, dates "
    "and intent as the original, in different wording and sentence structure. You output only the rewritten document."
)
PARA_USER = """Rewrite the body of this e-mail in different words. Rules:
- Keep every header line (From, To, Cc, Sent, Date, Subject, and the headers of quoted earlier messages) exactly as it is.
- Paraphrase every sentence of every body, including quoted earlier messages: different vocabulary and sentence structure, same meaning, same length within about 20%.
- Keep every name, number, date, amount, product, place and attachment reference unchanged.
- Do not add, drop or summarise information. Do not add commentary.
Output only the rewritten document.

<<<
{doc}
>>>"""


def _json_block(text: str) -> dict | None:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def apply_edits(doc: str, edits: list[dict]) -> tuple[str, str | None]:
    """Apply find/replace edits; return (new_text, error)."""
    out = doc
    for e in edits:
        old, new = e.get("old", ""), e.get("new", "")
        if not old:
            return doc, "empty old"
        n = out.count(old)
        if n == 0:
            return doc, "old not found"
        out = out.replace(old, new)  # n > 1 happens when a Subject line recurs in a quoted copy; replacing all keeps the thread consistent
    if out == doc:
        return doc, "no change"
    return out, None


async def make_edits(coll: str, concurrency: int = 6, limit: int | None = None, log=print) -> dict:
    src = read_jsonl(DATA / f"t2_{coll}.jsonl")
    out_path = DATA / f"t2_{coll}__edited.jsonl"
    done = {r["id"] for r in read_jsonl(out_path)}
    todo = [r for r in src if r["id"] not in done][: limit or None]
    if not todo:
        log(f"T2 edits {coll}: nothing to do ({len(done)} done)")
        return {"coll": coll, "new": 0}
    ts = TaskSet.load(ROOT / T2_TASKS[coll])
    client = TextClient(MODELS[LUNA])
    sem = asyncio.Semaphore(concurrency)
    stats = {"ok": 0, "infeasible": 0, "failed": 0, "cost": 0.0}
    lock = asyncio.Lock()

    async def one(r: dict):
        q = ts.questions[r["meta"]["target_qid"]]
        old_label = r["meta"]["old_label"]
        status = "RESPONSIVE" if old_label == "responsive" else "NOT responsive"
        goal = "NOT responsive" if old_label == "responsive" else "responsive"
        prompt = EDIT_USER.format(title=q.title, rfp=q.rfp_text, pos=q.positive_desc, neg=q.negative_desc, status=status, goal=goal, doc=r["text"])
        cost = 0.0
        result, err, edits, note, feasible = None, None, [], "", True
        async with sem:
            for attempt in range(2):
                c = await client.complete(EDIT_SYSTEM, prompt if attempt == 0 else prompt + f"\n\nYour previous answer failed: {err}. Copy the \"old\" text exactly from the document.", max_tokens=900)
                cost += c.cost_usd
                js = _json_block(c.text)
                if js is None:
                    err = "no JSON"
                    continue
                feasible = bool(js.get("feasible", True))
                edits = js.get("edits") or []
                note = str(js.get("note", ""))[:200]
                if not feasible:
                    break
                result, err = apply_edits(r["text"], edits)
                if err is None:
                    break
        new_label = "not_responsive" if old_label == "responsive" else "responsive"
        row = {"id": r["id"], "text": result if (feasible and err is None) else r["text"], "labels": {r["meta"]["target_qid"]: new_label}, "gray": [],
               "meta": {**r["meta"], "new_label": new_label, "feasible": feasible, "applied": feasible and err is None, "error": err, "edits": edits,
                        "note": note, "edit_chars": sum(len(e.get("old", "")) + len(e.get("new", "")) for e in edits), "edit_model": LUNA}}
        async with lock:
            append_jsonl(out_path, row)
            ledger_add("t2_edit", LUNA, cost, note=coll)
            stats["cost"] += cost
            stats["ok" if row["meta"]["applied"] else ("infeasible" if not feasible else "failed")] += 1

    try:
        await asyncio.gather(*(one(r) for r in todo))
    finally:
        await client.aclose()
    log(f"T2 edits {coll}: {stats}")
    return {"coll": coll, "new": len(todo), **stats}


async def make_paraphrases(corpus: str, concurrency: int = 6, limit: int | None = None, log=print) -> dict:
    src = read_jsonl(DATA / f"t3_{corpus}.jsonl")
    out_path = DATA / f"t3_{corpus}__para.jsonl"
    done = {r["id"] for r in read_jsonl(out_path)}
    todo = [r for r in src if r["id"] not in done][: limit or None]
    if not todo:
        log(f"T3 paraphrases {corpus}: nothing to do ({len(done)} done)")
        return {"corpus": corpus, "new": 0}
    client = TextClient(MODELS[LUNA])
    sem = asyncio.Semaphore(concurrency)
    stats = {"ok": 0, "failed": 0, "cost": 0.0}
    lock = asyncio.Lock()

    async def one(r: dict):
        async with sem:
            c = await client.complete(PARA_SYSTEM, PARA_USER.format(doc=r["text"]), max_tokens=max(400, int(len(r["text"]) / 2.2)))
        text = c.text.strip()
        text = re.sub(r"^<<<\s*|\s*>>>$", "", text).strip() + "\n"
        ok = len(text) > 0.5 * len(r["text"]) and text.strip() != r["text"].strip()
        sim = difflib.SequenceMatcher(None, r["text"], text).ratio()
        row = {"id": r["id"], "text": text if ok else r["text"], "labels": r["labels"], "gray": r["gray"],
               "meta": {**r["meta"], "applied": ok, "similarity": round(sim, 4), "len_ratio": round(len(text) / max(1, len(r["text"])), 3), "para_model": LUNA}}
        async with lock:
            append_jsonl(out_path, row)
            ledger_add("t3_para", LUNA, c.cost_usd, note=corpus)
            stats["cost"] += c.cost_usd
            stats["ok" if ok else "failed"] += 1

    try:
        await asyncio.gather(*(one(r) for r in todo))
    finally:
        await client.aclose()
    log(f"T3 paraphrases {corpus}: {stats}")
    return {"corpus": corpus, "new": len(todo), **stats}

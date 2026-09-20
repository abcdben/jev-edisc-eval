"""Stage 1 of synthetic corpus generation: the manifest.

For each arc in the bible, a planner model (Claude Sonnet 5, not a contestant in
the small tier) produces threads of document specs. Each spec carries the gold
labels, gray flags with rationale, doc type, date, participants, and a gist the
writer must realize. Specs are the ground truth; writers must not change labels.

Output: veridian/manifest.jsonl (one spec per line).
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
BIBLE = (ROOT / "veridian" / "bible.md").read_text()
QIDS = [
    "rfp01_recall", "rfp02_design_history", "rfp03_complaints", "rfp04_fda", "rfp06_marketing",
    "rfp07_surgeon_payments", "rfp08_sales_scripts", "rfp09_registry_decision", "rfp13_financials", "rfp17_personnel",
]
RFP_NUM = {1: "rfp01_recall", 2: "rfp02_design_history", 3: "rfp03_complaints", 4: "rfp04_fda", 6: "rfp06_marketing",
           7: "rfp07_surgeon_payments", 8: "rfp08_sales_scripts", 9: "rfp09_registry_decision", 13: "rfp13_financials", 17: "rfp17_personnel"}

DocType = Literal[
    "email", "email_thread", "chat", "text_message", "memo", "report", "minutes", "agenda", "spreadsheet_summary",
    "letter", "form", "calendar_invite", "presentation_notes",
]


class DocSpec(BaseModel):
    thread_id: str = Field(description="Short id shared by documents in the same thread, e.g. A3-t04")
    seq: int = Field(description="Order within the thread, starting at 1")
    doc_type: DocType
    date: str = Field(description="YYYY-MM-DD within the timeline")
    author: str = Field(description="Full name from the cast, or an invented minor character")
    recipients: list[str] = Field(description="Full names; empty for memos/forms/reports if none")
    subject: str = Field(description="Email subject / chat channel / document title")
    gist: str = Field(description="3-6 sentences: what the document says, what facts/numbers/lot numbers/names appear, where responsive content sits (top, quoted history, last message), tone. Enough for a writer to produce a consistent document.")
    words: int = Field(description="Target length in words")
    responsive_to: list[int] = Field(description="RFP numbers this document is responsive to (from the arc's allowed set). Empty if not responsive to any.")
    gray: list[int] = Field(description="Subset of RFP numbers (responsive or not) where a careful reviewer could reasonably disagree with the gold call")
    gray_rationale: str = Field(description="One sentence per gray RFP explaining the debate; empty if none")
    buried: bool = Field(description="True if the responsive content is not in the top message/first paragraph")


class ArcPlan(BaseModel):
    docs: list[DocSpec]


ARCS: dict[str, dict] = {
    # positive arcs: (allowed RFPs, target docs)
    "A1": {"allowed": [1, 3, 4], "n": 130, "desc": "Recall execution"},
    "A2": {"allowed": [2, 9], "n": 120, "desc": "Design history"},
    "A3": {"allowed": [3, 4, 9], "n": 130, "desc": "Metal-ion complaints"},
    "A4": {"allowed": [4, 3, 2], "n": 110, "desc": "FDA correspondence"},
    "A5": {"allowed": [6, 8], "n": 130, "desc": "Marketing claims"},
    "A6": {"allowed": [7, 6], "n": 120, "desc": "Surgeon payments"},
    "A7": {"allowed": [8, 6, 9], "n": 110, "desc": "Sales scripts & objection handling"},
    "A8": {"allowed": [9, 3, 4, 13], "n": 120, "desc": "Registry signal & decision"},
    "A9": {"allowed": [13, 9], "n": 110, "desc": "Financials"},
    "A10": {"allowed": [17], "n": 110, "desc": "Personnel"},
    "A11": {"allowed": [1, 2, 3, 4, 6, 7, 8, 9, 13, 17], "n": 100, "desc": "Cross-cutting threads"},
    "N1": {"allowed": [2, 3, 4, 6, 9], "n": 90, "desc": "KneeFlex (hard negative; Apex only in passing)", "negative": True},
    "N2": {"allowed": [], "n": 40, "desc": "ClassicHip phase-out (hard negative)", "negative": True},
    "N3": {"allowed": [6, 13, 1], "n": 70, "desc": "Apex logistics with no substance (hard negative/gray)", "negative": True},
    "N4": {"allowed": [17], "n": 50, "desc": "Other-employee HR (hard negative)", "negative": True},
    "N5": {"allowed": [13, 9], "n": 50, "desc": "General corporate (hard negative/gray)", "negative": True},
    "Z1": {"allowed": [], "n": 80, "desc": "HR/benefits noise", "noise": True},
    "Z2": {"allowed": [], "n": 80, "desc": "IT noise", "noise": True},
    "Z3": {"allowed": [], "n": 60, "desc": "Facilities/admin noise", "noise": True},
    "Z4": {"allowed": [], "n": 80, "desc": "Social noise", "noise": True},
    "Z5": {"allowed": [], "n": 70, "desc": "Vendor/newsletter noise", "noise": True},
    "Z6": {"allowed": [], "n": 60, "desc": "Personal-ish noise", "noise": True},
}

CHUNK = 25  # docs per planner call

PLANNER_SYSTEM = """You are the showrunner for a synthetic eDiscovery corpus. You plan documents; other writers will render them.
You are given a matter bible. Produce a manifest of document specifications for one arc of the story.

Rules you must follow exactly:
- Every spec's `responsive_to` must be a subset of the arc's ALLOWED RFP numbers. Labels are gold truth; think like a careful, slightly inclusive document reviewer applying the RFP text in the bible's task definitions. A document is responsive to an RFP if a reviewer applying that RFP would produce it.
- Group documents into realistic threads (2-6 documents) plus some standalone documents. Threads evolve: replies add information, people get cc'd, topics drift. Later messages in a thread may be responsive when earlier ones were not, and vice versa.
- Within positive arcs, roughly 15-25% of documents should be hard negatives: same people and same week, adjacent topic, NOT responsive to any RFP (e.g. scheduling with no substance, the same team discussing a different product, an out-of-office reply). Mark those with empty responsive_to.
- About 10-15% of documents should be gray for at least one RFP, with a concrete rationale. Assign the gold the inclusive way and explain the debate.
- About 20% of responsive documents should be `buried` (responsive content only in quoted history or in the last message of a long email chain, or one line deep in a long memo).
- Mix document types per the bible's distribution. Vary length: chats 30-120 words, emails 40-350, memos/reports 300-900, minutes 200-500, forms 150-400, spreadsheet summaries 150-400.
- Use the cast, dates, lot numbers, product names, and facts from the bible. Use realistic specifics (TrackWise IDs, ECO numbers, dollar figures, percentages, hospital names). Invent minor characters where needed and reuse them within a thread.
- Dates must be consistent with the timeline and with thread order.
- Gists must be concrete enough that a writer who has the bible can write the document without inventing contradicting facts. Name the specific facts to include. Say where the responsive content sits.
- Never reference the benchmark, RFP numbers, labels, or fiction inside `subject` or `gist` content that a writer would copy. (The `gist` may describe placement like "the responsive part is in the quoted message", that is fine, but no "RFP 3" in the document text itself.)
- Return exactly the number of documents requested."""


def _prompt(arc: str, n: int, chunk_idx: int, n_chunks: int, existing_threads: list[str]) -> str:
    a = ARCS[arc]
    allowed = ", ".join(str(x) for x in a["allowed"]) or "none (no document in this arc is responsive to any RFP)"
    kind = "NOISE ARC: none of these documents are responsive to anything. They must look like real corporate email/chat/admin traffic at Veridian; they may mention products by name in passing only in innocent ways (e.g. 'the Apex booth shipping crate arrived'). gray must be empty." if a.get("noise") else (
        "HARD-NEGATIVE ARC: the default is NOT responsive. Only a small number (at most 15%) may be gray or responsive, and only where the bible's gray guidance says a careful inclusive reviewer would call it. Use the allowed list only for those gray/edge cases." if a.get("negative") else
        "POSITIVE ARC: most documents (75-85%) are responsive to at least one allowed RFP; about 30% of responsive docs should be responsive to 2+ allowed RFPs where that is natural."
    )
    threads = f"Thread ids already used (do not reuse): {', '.join(existing_threads)}" if existing_threads else ""
    return f"""<bible>
{BIBLE}
</bible>

ARC {arc}: {a['desc']}
ALLOWED RFP numbers for this arc: {allowed}
{kind}

This is chunk {chunk_idx + 1} of {n_chunks} for this arc; cover a different slice of the storyline/time period than other chunks would (chunk {chunk_idx + 1} should lean toward the {'earlier' if chunk_idx == 0 else 'later' if chunk_idx == n_chunks - 1 else 'middle'} part of the arc's timeline). Thread ids must be of the form {arc}-c{chunk_idx + 1}-tNN.
{threads}

Produce exactly {n} document specs."""


async def plan_arc(client: anthropic.AsyncAnthropic, arc: str, out: Path, model: str = "claude-sonnet-5", log=print) -> list[dict]:
    a = ARCS[arc]
    n_total = a["n"]
    n_chunks = max(1, round(n_total / CHUNK))
    sizes = [n_total // n_chunks + (1 if i < n_total % n_chunks else 0) for i in range(n_chunks)]
    specs: list[dict] = []
    for i, n in enumerate(sizes):
        schema = ArcPlan.model_json_schema()
        _strict(schema)
        for attempt in range(3):
            try:
                resp = await client.messages.create(
                    model=model,
                    max_tokens=24000,
                    thinking={"type": "disabled"},
                    system=PLANNER_SYSTEM,
                    messages=[{"role": "user", "content": _prompt(arc, n, i, n_chunks, [])}],
                    output_config={"format": {"type": "json_schema", "schema": schema}, "effort": "medium"},
                )
                text = "".join(b.text for b in resp.content if b.type == "text")
                if resp.stop_reason == "max_tokens":
                    raise RuntimeError(f"truncated at {resp.usage.output_tokens} output tokens")
                plan = ArcPlan.model_validate_json(text)
                break
            except Exception as e:  # noqa: BLE001
                log(f"[plan {arc} chunk {i}] attempt {attempt} failed: {e}")
                if attempt == 2:
                    raise
        allowed = set(a["allowed"])
        for d in plan.docs:
            row = d.model_dump()
            row["arc"] = arc
            row["responsive_to"] = sorted(set(x for x in row["responsive_to"] if x in allowed))
            row["gray"] = sorted(set(x for x in row["gray"] if x in RFP_NUM))
            if a.get("noise"):
                row["responsive_to"], row["gray"] = [], []
            specs.append(row)
        cost = (resp.usage.input_tokens * 3 + resp.usage.output_tokens * 15) / 1e6
        log(f"[plan {arc}] chunk {i+1}/{n_chunks}: {len(plan.docs)} specs, {resp.usage.output_tokens} out tok, ${cost:.2f}")
    return specs


def _strict(schema: dict) -> None:
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node.setdefault("additionalProperties", False)
            if node.get("type") in ("number", "integer"):
                node.pop("minimum", None); node.pop("maximum", None)
            for v in list(node.values()):
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(schema)


async def plan_all(out: Path, arcs: list[str] | None = None, concurrency: int = 4, log=print) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    client = anthropic.AsyncAnthropic(max_retries=5, timeout=600.0)
    arcs = arcs or list(ARCS)
    done: dict[str, list[dict]] = {}
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.setdefault(r["arc"], []).append(r)
    todo = [a for a in arcs if a not in done]
    log(f"planning arcs: {todo} (already done: {sorted(done)})")
    sem = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()

    async def one(arc):
        async with sem:
            specs = await plan_arc(client, arc, out, log=log)
        async with lock:
            with out.open("a") as f:
                for s in specs:
                    f.write(json.dumps(s) + "\n")

    await asyncio.gather(*(one(a) for a in todo))
    await client.close()


def finalize_manifest(src: Path, dst: Path, seed: int = 7) -> None:
    """Assign stable doc ids in shuffled order, map RFP numbers to qids, write final manifest."""
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    rng = random.Random(seed)
    rng.shuffle(rows)
    # keep threads contiguous is not required; ids are opaque
    with dst.open("w") as f:
        for i, r in enumerate(rows):
            r["id"] = f"VRD-{i+1:05d}"
            r["labels"] = {RFP_NUM[n]: "responsive" for n in r["responsive_to"]}
            r["gray_q"] = [RFP_NUM[n] for n in r["gray"] if n in RFP_NUM]
            f.write(json.dumps(r) + "\n")


def manifest_stats(path: Path) -> str:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    from collections import Counter
    pos = Counter(); gray = Counter(); types = Counter(); arcs = Counter(); multi = 0
    for r in rows:
        for n in r["responsive_to"]:
            pos[RFP_NUM[n]] += 1
        for n in r["gray"]:
            gray[RFP_NUM.get(n, n)] += 1
        types[r["doc_type"]] += 1
        arcs[r["arc"]] += 1
        if len(r["responsive_to"]) > 1:
            multi += 1
    lines = [f"{len(rows)} docs; {sum(1 for r in rows if r['responsive_to'])} responsive to >=1; {multi} multi-RFP; {sum(1 for r in rows if r['gray'])} gray"]
    for q in QIDS:
        lines.append(f"  {q:<24} pos={pos[q]:<4} gray={gray[q]}")
    lines.append("  types: " + ", ".join(f"{k}={v}" for k, v in types.most_common()))
    lines.append("  arcs: " + ", ".join(f"{k}={v}" for k, v in sorted(arcs.items())))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    out = ROOT / "veridian" / "manifest_raw.jsonl"
    arcs = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    asyncio.run(plan_all(out, arcs))
    finalize_manifest(out, ROOT / "veridian" / "manifest.jsonl")
    print(manifest_stats(ROOT / "veridian" / "manifest.jsonl"))

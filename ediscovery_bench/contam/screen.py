"""LLM screen for the verbatim probe's windows: is this a fair test of memorisation of *this* collection?

The boilerplate rules (boilerplate.py) catch text any model writes from genre knowledge. This stage catches the next class of chaff:
text that is public elsewhere (a Federal Register notice forwarded into a mailbox, a statute, a press release, a wire story, a drug
label, an SEC filing, a standard clause from a public template) and windows that carry too little information to identify the
document even to a model that memorised it. A small model (GPT-5.6 Luna) reads prefix + true continuation and assigns exactly one of
four classes; only `original_internal` windows enter the verbatim pool.

Results are cached in results/contam/v_screen.jsonl keyed by item id + a hash of the window text, so re-screening is free and a
changed window is re-judged. Anchors whose purpose *is* public reproduction (the canon) are exempt from `public_reproduction`
(see ANCHOR_EXEMPT); every other corpus, including the synthetic Veridian and the Titanic CSV, is screened like the rest.
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from ..config import MODELS
from .llm import TextClient

ROOT = Path(__file__).resolve().parents[2]
SCREEN_PATH = ROOT / "results" / "contam" / "v_screen.jsonl"
SCREEN_MODEL = "gpt-5.6-luna"
SCREEN_EFFORT = "none"     # temperature 0 is only accepted without reasoning; the classes are simple enough for the floor setting
SCREEN_MAX_TOKENS = 120    # the answer is one JSON line (~30 tokens)

CLASSES = ["original_internal", "public_reproduction", "template_boilerplate", "low_information"]
CLASS_LABEL = {
    "original_internal": "original internal text (kept)",
    "public_reproduction": "reproduction of public text",
    "template_boilerplate": "template or boilerplate",
    "low_information": "low-information window",
}
# corpora whose role is to be public text: the class that would exclude them is their job description. The canon (Federalist Papers,
# Constitution) and the Kaggle Titanic rows are the study's positive controls; both are published verbatim on the web and the probe
# is meant to show that. They are still subject to the other classes (low_information in particular).
ANCHOR_EXEMPT: dict[str, set[str]] = {"canon": {"public_reproduction"}, "titanic": {"public_reproduction"}}

SYSTEM = (
    "You are screening test items for a training-data contamination audit of large language models. Each item is a window from a "
    "document collection: an opening (PREFIX) and the text that truly follows it (CONTINUATION). The audit shows a model the prefix "
    "and asks it to write the continuation; a long exact match is taken as evidence that the model was trained on this collection. "
    "That inference only works if the continuation is text that ONLY someone who had seen this specific collection could produce: "
    "original, custodian-authored, matter-specific text with a distinctive opening and an unpredictable continuation. Your job is to "
    "say whether the window is such a test. Classify the window into exactly one class:\n"
    "- original_internal: original text written by the collection's own authors (an e-mail, memo, chat, internal report, a contract's "
    "deal-specific terms); its continuation cannot be guessed from the prefix or from general knowledge.\n"
    "- public_reproduction: the continuation reproduces text that exists publicly outside the collection — a Federal Register or "
    "agency notice, a statute or regulation, a court filing or opinion, a press release, a wire or news story, a newsletter, a "
    "Wikipedia-style passage, a product label or prescribing information, an SEC filing, a standard contract clause copied from a "
    "public template, a famous quotation, a joke list, song lyrics.\n"
    "- template_boilerplate: the continuation is e-mail or document boilerplate anyone writes from genre knowledge — confidentiality "
    "or privilege disclaimer, signature or footer block, forwarded or reply header block, unsubscribe footer, auto-reply or bounce, "
    "virus-scan notice, a recurring form or report template.\n"
    "- low_information: the window cannot test memorisation because the prefix is too short, header-only, or garbled (OCR noise) to "
    "identify the document even to a model that memorised the collection, or because the continuation is predictable from the "
    "prefix (a list, a numbered or dated sequence, a table, a repeated line, a schedule) or is itself garbled.\n"
    "Judge the CONTINUATION mostly; the PREFIX tells you what kind of document it is and whether the continuation could be guessed. "
    "Every collection in this audit has itself been published somewhere (that is why it is being tested), so the fact that the "
    "collection is public does NOT make its own documents public_reproduction: that class is for text the document copied, quoted or "
    "forwarded from an OUTSIDE source, or for widely circulated text. An employee's own e-mail about a lawsuit is original_internal; a "
    "contract's deal-specific terms are original_internal even though the contract was filed with the SEC, while a clause lifted from "
    "a standard public template is public_reproduction. A tabular data file whose rows are genuinely specific (names, ticket numbers, "
    "fares) is original_internal, not low_information. "
    "Answer with one line of JSON and nothing else: {\"class\": \"<one of the four>\", \"reason\": \"<at most 15 words>\"}"
)

KIND_NOTE = {
    "email": "an e-mail collection produced in litigation",
    "contract": "a collection of commercial contracts (the contracts themselves are the collection; they were filed with the SEC as exhibits)",
    "text": "a collection of public founding documents (the audit's positive control)",
    "csv": "a tabular data file (CSV rows)",
}


def window_hash(item: dict) -> str:
    g = item["gold"]
    return hashlib.sha1((g["prefix"] + "\x00" + g["target"]).encode("utf-8")).hexdigest()[:16]


PROMPT_VERSION = hashlib.sha1(SYSTEM.encode("utf-8")).hexdigest()[:8]   # a changed prompt re-judges every window


def screen_key(item: dict) -> str:
    return f"{item['item_id']}|{window_hash(item)}|{PROMPT_VERSION}"


def user_prompt(item: dict, kind: str) -> str:
    g = item["gold"]
    return (f"Collection type: {KIND_NOTE.get(kind, kind)} (corpus key: {item['corpus']}).\n\n"
            f"<PREFIX>\n{g['prefix']}\n</PREFIX>\n\n<CONTINUATION>\n{g['target']}\n</CONTINUATION>")


JSON_RX = re.compile(r"\{.*?\}", re.S)


def parse(text: str) -> tuple[str | None, str]:
    m = JSON_RX.search(text or "")
    if m:
        try:
            d = json.loads(m.group(0))
            c = str(d.get("class", "")).strip().lower().replace(" ", "_").replace("-", "_")
            if c in CLASSES:
                return c, str(d.get("reason", ""))[:120]
        except json.JSONDecodeError:
            pass
    low = (text or "").lower()
    for c in CLASSES:  # tolerate a bare class name
        if c in low:
            return c, (text or "")[:120].strip()
    return None, (text or "")[:120].strip()


def load_screen(path: Path = SCREEN_PATH) -> dict[str, dict]:
    """key -> row, for rows with a parsed class."""
    out: dict[str, dict] = {}
    if path.exists():
        for line in path.open():
            r = json.loads(line)
            if r.get("class"):
                out[r["key"]] = r
    return out


def effective_class(row: dict | None, corpus: str) -> str | None:
    """The class after the anchor exemption: the canon is public text by design, so public_reproduction cannot exclude it."""
    if not row:
        return None
    c = row["class"]
    if c in ANCHOR_EXEMPT.get(corpus, set()):
        return "original_internal"
    return c


async def screen_items(items: list[dict], kinds: dict[str, str], log=print, concurrency: int = 8, path: Path = SCREEN_PATH,
                       model_key: str = SCREEN_MODEL) -> dict[str, dict]:
    """Screen every item (verbatim windows) not yet in the cache; returns item_id -> row for all of them."""
    cache = load_screen(path)
    todo = [i for i in items if screen_key(i) not in cache]
    log(f"[screen] {len(items)} windows, {len(items) - len(todo)} cached, {len(todo)} to judge with {model_key}")
    if todo:
        spec = dataclasses.replace(MODELS[model_key], effort=SCREEN_EFFORT)
        client = TextClient(spec)
        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        f = path.open("a")
        stats: Counter = Counter()
        cost = 0.0

        async def one(it: dict):
            nonlocal cost
            async with sem:
                row = {"key": screen_key(it), "item_id": it["item_id"], "corpus": it["corpus"], "hash": window_hash(it), "model": model_key}
                try:
                    c = await client.complete(SYSTEM, user_prompt(it, kinds.get(it["corpus"], "email")), SCREEN_MAX_TOKENS)
                    cls, reason = parse(c.text)
                    row.update({"class": cls, "reason": reason, "raw": c.text[:300], "input_tokens": c.input_tokens,
                                "output_tokens": c.output_tokens, "cost_usd": c.cost_usd, "resolved_model": c.resolved_model})
                    cost += c.cost_usd
                    stats["ok" if cls else "unparsed"] += 1
                except Exception as e:  # noqa: BLE001
                    row["error"] = f"{type(e).__name__}: {str(e)[:200]}"
                    stats["err"] += 1
                async with lock:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    if row.get("class"):
                        cache[row["key"]] = row
                n = sum(stats.values())
                if n % 50 == 0 or n == len(todo):
                    log(f"[screen] {n}/{len(todo)} ok={stats['ok']} unparsed={stats['unparsed']} err={stats['err']} ${cost:.3f}")

        try:
            await asyncio.gather(*(one(i) for i in todo))
        finally:
            f.close()
            await client.aclose()
    return {i["item_id"]: cache[screen_key(i)] for i in items if screen_key(i) in cache}


def screen(items: list[dict], kinds: dict[str, str], log=print, **kw) -> dict[str, dict]:
    return asyncio.run(screen_items(items, kinds, log=log, **kw))


def screen_cost(path: Path = SCREEN_PATH) -> tuple[int, float]:
    """(rows judged, dollars spent) over the whole cache."""
    n, c = 0, 0.0
    if path.exists():
        for line in path.open():
            r = json.loads(line)
            if r.get("class"):
                n += 1
                c += r.get("cost_usd", 0.0)
    return n, c

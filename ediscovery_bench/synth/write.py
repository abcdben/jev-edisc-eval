"""Stage 2: render each manifest spec into a document.

Authorship rotates by thread across three model families so no single
contestant vendor wrote the whole test set, and `meta.author_model` lets us
check for author-family bias in the results. Threads are written in order so
replies can quote the earlier messages verbatim.

Output: data/veridian/veridian.jsonl  ({"id","text","labels","gray","meta"})
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from collections import defaultdict
from pathlib import Path

import anthropic
import openai
from google import genai
from google.genai import types as gt

ROOT = Path(__file__).resolve().parents[2]
BIBLE = (ROOT / "veridian" / "bible.md").read_text()

WRITER_MODELS = ["claude-sonnet-5", "gpt-5.6-terra", "gemini-3.8-flash"]

WRITER_SYSTEM = """You write realistic corporate documents for a fictional medical-device company, Veridian Orthopedics. You are given the matter bible (cast, products, timeline, style rules), a specification for one document, and any earlier documents in the same thread.

Write the document exactly as it would exist in the company's files. Rules:
- Follow the spec's doc_type, date, author, recipients, subject, target length, and gist. Every fact named in the gist must appear. Do not contradict the bible or earlier thread documents.
- Use the header formats from the bible's style guide (From/To/Cc/Date/Subject for email; timestamped lines for chats and texts; a title block for memos, reports, minutes, forms, letters). Emails in a thread with earlier messages must include the quoted history below the new text, using "-----Original Message-----" or "On <date>, <name> wrote:" with the earlier message's headers and text reproduced.
- Match the author's voice from the bible. Real people ramble, hedge, typo (in chats/phone emails), and sometimes ignore questions. Do not write like a summary.
- If the spec says the responsive content is buried, keep the top of the document about something else and put the substantive content where the spec says.
- Never mention RFPs, requests for production, responsiveness, labels, benchmarks, or that anything is fictional. No placeholders or brackets like [Name].
- Output only the document text. No preamble, no markdown code fences, no commentary."""


def _spec_block(spec: dict, prior: list[tuple[dict, str]]) -> str:
    s = {k: spec[k] for k in ("doc_type", "date", "author", "recipients", "subject", "words", "gist", "buried")}
    parts = [f"<bible>\n{BIBLE}\n</bible>", f"<spec>\n{json.dumps(s, indent=1)}\n</spec>"]
    if prior:
        hist = "\n\n".join(f"<earlier seq=\"{p['seq']}\" date=\"{p['date']}\">\n{t}\n</earlier>" for p, t in prior)
        parts.append(f"<thread_history>\n{hist}\n</thread_history>")
    parts.append("Write the document now.")
    return "\n\n".join(parts)


class Writers:
    def __init__(self):
        self.anth = anthropic.AsyncAnthropic(max_retries=6, timeout=300.0)
        self.oai = openai.AsyncOpenAI(max_retries=6, timeout=300.0)
        self.gem = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
            http_options=gt.HttpOptions(timeout=300_000, retry_options=gt.HttpRetryOptions(attempts=6, max_delay=30.0)),
        )
        self.spend = defaultdict(float)

    async def write(self, model: str, spec: dict, prior: list[tuple[dict, str]]) -> str:
        user = _spec_block(spec, prior)
        max_out = min(4000, int(spec["words"] * 2.2) + 400 + sum(len(t) // 3 for _, t in prior))
        if model == "claude-sonnet-5":
            r = await self.anth.messages.create(
                model="claude-sonnet-5", max_tokens=max_out, system=WRITER_SYSTEM,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": f"<bible>\n{BIBLE}\n</bible>", "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": user.split("</bible>", 1)[1]},
                ]}],
                thinking={"type": "disabled"}, output_config={"effort": "low"},
            )
            text = "".join(b.text for b in r.content if b.type == "text")
            u = r.usage
            self.spend[model] += ((u.input_tokens * 2.0) + (getattr(u, "cache_read_input_tokens", 0) or 0) * 0.2
                                  + (getattr(u, "cache_creation_input_tokens", 0) or 0) * 2.5 + u.output_tokens * 10.0) / 1e6
        elif model == "gpt-5.6-terra":
            r = await self.oai.responses.create(
                model="gpt-5.6-terra", instructions=WRITER_SYSTEM, input=user, reasoning={"effort": "none"},
                max_output_tokens=max_out, store=False, prompt_cache_key="veridian-writer",
            )
            text = r.output_text
            u = r.usage
            cached = (u.input_tokens_details.cached_tokens or 0) if u.input_tokens_details else 0
            self.spend[model] += ((u.input_tokens - cached) * 2.0 + cached * 0.2 + u.output_tokens * 12.0) / 1e6
        else:
            r = await self.gem.aio.models.generate_content(
                model="gemini-3.8-flash", contents=user,
                config=gt.GenerateContentConfig(system_instruction=WRITER_SYSTEM, max_output_tokens=max_out,
                                                thinking_config=gt.ThinkingConfig(thinking_level="low")),
            )
            text = r.text or ""
            um = r.usage_metadata
            cached = (um.cached_content_token_count or 0) if um else 0
            self.spend[model] += (((um.prompt_token_count or 0) - cached) * 0.75 + cached * 0.075
                                  + ((um.candidates_token_count or 0) + (um.thoughts_token_count or 0)) * 3.75) / 1e6
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if not text:
            raise RuntimeError("empty document")
        return text

    async def aclose(self):
        await self.anth.close(); await self.oai.close()


async def write_all(manifest: Path, out: Path, concurrency: int = 6, log=print, seed: int = 11) -> None:
    specs = [json.loads(l) for l in manifest.read_text().splitlines() if l.strip()]
    threads: dict[str, list[dict]] = defaultdict(list)
    for s in specs:
        threads[s["thread_id"]].append(s)
    for t in threads.values():
        t.sort(key=lambda s: s["seq"])
    # deterministic rotation by thread, balanced across families
    tids = sorted(threads)
    random.Random(seed).shuffle(tids)
    assign = {tid: WRITER_MODELS[i % 3] for i, tid in enumerate(tids)}

    done: dict[str, dict] = {}
    if out.exists():
        for l in out.read_text().splitlines():
            if l.strip():
                r = json.loads(l); done[r["id"]] = r
    out.parent.mkdir(parents=True, exist_ok=True)
    w = Writers()
    sem = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    n_new = 0

    async def one_thread(tid: str):
        nonlocal n_new
        model = assign[tid]
        prior: list[tuple[dict, str]] = []
        for spec in threads[tid]:
            if spec["id"] in done:
                prior.append((spec, done[spec["id"]]["text"]))
                continue
            async with sem:
                text = None
                for attempt in range(3):
                    try:
                        text = await w.write(model, spec, prior[-3:])
                        break
                    except Exception as e:  # noqa: BLE001
                        log(f"[write {spec['id']} {model}] attempt {attempt}: {type(e).__name__}: {str(e)[:200]}")
                        await asyncio.sleep(3 * (attempt + 1))
                if text is None:
                    # fall back to another family rather than lose the doc
                    alt = WRITER_MODELS[(WRITER_MODELS.index(model) + 1) % 3]
                    text = await w.write(alt, spec, prior[-3:])
                    used = alt
                else:
                    used = model
            row = {
                "id": spec["id"], "text": text, "labels": spec["labels"], "gray": spec["gray_q"],
                "meta": {"arc": spec["arc"], "thread_id": tid, "seq": spec["seq"], "doc_type": spec["doc_type"],
                         "date": spec["date"], "author": spec["author"], "author_model": used, "buried": spec["buried"],
                         "gray_rationale": spec["gray_rationale"], "words_target": spec["words"]},
            }
            async with lock:
                with out.open("a") as f:
                    f.write(json.dumps(row) + "\n")
                n_new += 1
                if n_new % 50 == 0:
                    log(f"[write] {n_new} new docs; spend " + ", ".join(f"{k}=${v:.2f}" for k, v in w.spend.items()))
            prior.append((spec, text))

    await asyncio.gather(*(one_thread(t) for t in tids))
    await w.aclose()
    log(f"[write] done: {n_new} new docs; spend " + ", ".join(f"{k}=${v:.2f}" for k, v in w.spend.items()))


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    man = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "veridian" / "manifest.jsonl"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "veridian" / "veridian.jsonl"
    asyncio.run(write_all(man, out))

"""Paraphrase arm (round 2): rewrite each document's body with GPT-5.6 Luna so that wording and sentence structure change while the
content the task depends on is preserved; verify preservation; and measure what the rewrite does to verbatim retrievability.

  paraphrase_rows()   resumable; one JSONL row per document in data/ablation/<arm>__paraphrased.cache.jsonl, then the arm file
                      is written in corpus order. Deterministic checks after every rewrite (numbers, quoted defined terms, capitalised
                      tokens, length); a failed check is retried once with the discrepancies listed, then flagged (meta.paraphrase_ok).
  fidelity_judge()    a second model (Terra) reads original + rewrite for a sample and lists any legal difference (JSON).
  memo_probe()        the contamination study's finish-the-document probe (contam.build.make_verbatim_item, contam.score.score_verbatim,
                      imported, not modified) on windows from every CUAD contract in three variants — original, renamed, paraphrased —
                      scored against the original continuation (does the model still retrieve the real text?) and the variant's own.

All OpenAI calls go through the flex tier at temperature 0 with reasoning.effort=none, like the classification runs; cost is
recorded per row as paid (flex, cache-adjusted) and list.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections import Counter
from pathlib import Path

from ..config import MODELS, ModelSpec
from ..providers.openai_ import CACHE_READ_MULT, FLEX_MULT

CONTRACT_SYSTEM = ("You are a legal drafting assistant performing a controlled rewrite for a text-processing experiment. "
                   "Output only the rewritten text: no preamble, no notes, no quotation marks around the whole text.")
CONTRACT_USER = (
    "Rewrite the contract excerpt below so that its wording and sentence structure differ substantially from the original while the "
    "legal content is preserved exactly.\n\n"
    "Preserve, verbatim and in the same order: every party name and other proper name; every capitalised defined term and every quoted "
    "definition (for example \"Effective Date\"); every number, amount, percentage, date, period and section cross-reference; every clause "
    "and sub-clause boundary with its numbering or lettering; and every obligation, right, condition, exception and remedy, binding the same "
    "parties with the same modality (shall / may / shall not).\n\n"
    "Change: vocabulary (synonyms for words that are not defined terms), sentence structure, voice (active/passive), the order of co-ordinated "
    "items where order has no legal meaning, and the phrasing of standard boilerplate. Do not summarise, interpret, add or omit anything. "
    "Do not add commentary. Return the rewritten excerpt only.{feedback}\n\n<excerpt>\n{body}\n</excerpt>"
)
EMAIL_SYSTEM = ("You are an editor performing a controlled rewrite for a text-processing experiment. Output only the rewritten text: no "
                "preamble, no notes.")
EMAIL_USER = (
    "Rewrite the body of the message below so that its wording and sentence structure differ substantially from the original while every "
    "fact is preserved: every person, organisation, product, place, number, date, time and amount; every statement, request, question, "
    "decision and attitude expressed; and the order in which they appear. Keep names, product codes and any quoted text verbatim. Keep "
    "greetings and sign-offs but reword them. Do not summarise, add or omit anything. Return the rewritten body only.{feedback}\n\n"
    "<message_body>\n{body}\n</message_body>"
)

NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
QUOTE_RE = re.compile(r"[\"“]([^\"”]{1,60})[\"”]")
CAP_RE = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][A-Za-z]{2,}\b")
SENT_START_RE = re.compile(r"(?:^|[.!?]\s+)([A-Z][A-Za-z]{2,})")


def split_header(text: str) -> tuple[str, str]:
    """(header, body). Contract excerpts: the two 'Contract:' / 'Excerpt' lines. E-mails: the header block up to the first blank line."""
    if "\n\n" in text:
        head, body = text.split("\n\n", 1)
        if head.startswith("Contract:") or re.search(r"^(From|To|Subject|Date|Sent|Cc):", head, re.M) or head.startswith("["):
            return head, body
    return "", text


def _nums(s: str) -> Counter:
    return Counter(n.replace(",", "").rstrip(".") for n in NUM_RE.findall(s))


def _quotes(s: str) -> set[str]:
    return {q.strip().lower() for q in QUOTE_RE.findall(s)}


def _caps(s: str) -> Counter:
    starts = Counter(SENT_START_RE.findall(s))
    c = Counter(re.findall(r"\b[A-Z][A-Za-z]{2,}\b", s))
    for k, v in starts.items():
        c[k] -= v
    return Counter({k: v for k, v in c.items() if v > 0})


def check(orig: str, para: str, genre: str) -> dict:
    n_o, n_p = _nums(orig), _nums(para)
    q_o, q_p = _quotes(orig), _quotes(para)
    c_o, c_p = _caps(orig), _caps(para)
    cap_hit = sum(min(v, c_p.get(k, 0)) for k, v in c_o.items())
    cap_tot = sum(c_o.values())
    ratio = len(para) / max(1, len(orig))
    missing_n = list((n_o - n_p).elements())
    extra_n = list((n_p - n_o).elements())
    out = {"numbers_ok": not missing_n and not extra_n, "missing_numbers": missing_n[:10], "extra_numbers": extra_n[:10],
           "quotes_ok": q_o <= q_p, "missing_quotes": sorted(q_o - q_p)[:10], "caps_recall": round(cap_hit / cap_tot, 3) if cap_tot else 1.0,
           "ratio": round(ratio, 3), "ratio_ok": 0.55 <= ratio <= 1.7}
    out["ok"] = out["numbers_ok"] and out["quotes_ok"] and out["ratio_ok"] and (out["caps_recall"] >= 0.8 if genre == "contract" else out["caps_recall"] >= 0.7)
    return out


def _feedback(c: dict) -> str:
    bits = []
    if c["missing_numbers"]:
        bits.append("these numbers from the original are missing: " + ", ".join(c["missing_numbers"]))
    if c["extra_numbers"]:
        bits.append("these numbers do not occur in the original: " + ", ".join(c["extra_numbers"]))
    if c["missing_quotes"]:
        bits.append("these quoted terms are missing: " + ", ".join(f"\"{q}\"" for q in c["missing_quotes"]))
    if c["caps_recall"] < 0.8:
        bits.append("several capitalised names or defined terms were dropped or altered; keep every one verbatim")
    if not c["ratio_ok"]:
        bits.append("the rewrite is much " + ("shorter" if c["ratio"] < 1 else "longer") + " than the original; keep the same level of detail")
    return (" A previous attempt failed verification: " + "; ".join(bits) + ". Fix these in this attempt.") if bits else ""


class FlexText:
    """Minimal OpenAI Responses client: flex tier, temperature 0, effort=none; returns (text, paid, list, in_tok, out_tok, cached)."""

    def __init__(self, spec: ModelSpec):
        import openai

        self.spec = spec
        self.client = openai.AsyncOpenAI(max_retries=6, timeout=300.0)
        self.flex = True
        self._temp_ok = True

    async def complete(self, system: str, user: str, max_tokens: int = 1200, cache_key: str | None = None) -> tuple[str, float, float, int, int, int]:
        import openai

        kwargs: dict = dict(model=self.spec.model_id, instructions=system, input=user, store=False, max_output_tokens=max_tokens)
        if self.spec.effort:
            kwargs["reasoning"] = {"effort": self.spec.effort}
        if cache_key:
            kwargs["prompt_cache_key"] = cache_key
        for _ in range(3):
            if self.flex:
                kwargs["service_tier"] = "flex"
            else:
                kwargs.pop("service_tier", None)
            if self._temp_ok:
                kwargs["temperature"] = 0
            else:
                kwargs.pop("temperature", None)
            try:
                resp = await self.client.responses.create(**kwargs)
                break
            except openai.BadRequestError as e:
                msg = str(e).lower()
                if self.flex and "service_tier" in msg:
                    self.flex = False
                    continue
                if self._temp_ok and "temperature" in msg:
                    self._temp_ok = False
                    continue
                raise
        u = resp.usage
        i, o = int(u.input_tokens or 0), int(u.output_tokens or 0)
        cached = int(u.input_tokens_details.cached_tokens or 0) if (u and u.input_tokens_details) else 0
        listed = self.spec.cost_usd(i, o)
        paid = ((i - cached) * self.spec.input_per_mtok + cached * self.spec.input_per_mtok * CACHE_READ_MULT + o * self.spec.output_per_mtok) / 1e6
        tier = getattr(resp, "service_tier", None) or ("flex" if self.flex else "default")
        if tier == "flex":
            paid *= FLEX_MULT
        return (resp.output_text or "").strip(), paid, listed, i, o, cached

    async def aclose(self):
        await self.client.close()


def _load_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {r["id"]: r for r in (json.loads(l) for l in path.read_text().split("\n") if l.strip())}


async def paraphrase_rows(rows: list[dict], genre: str, cache_path: Path, model: str = "gpt-5.6-luna", concurrency: int = 16,
                          max_retries: int = 1, log=print) -> tuple[list[dict], dict]:
    """Returns (paraphrased rows in input order, stats). Resumable via cache_path."""
    cache = _load_cache(cache_path)
    todo = [r for r in rows if r["id"] not in cache]
    spec = MODELS[model]
    client = FlexText(spec)
    sem = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    spent = {"paid": 0.0, "list": 0.0, "calls": 0}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    async def one(r: dict):
        head, body = split_header(r["text"])
        system, tmpl = (CONTRACT_SYSTEM, CONTRACT_USER) if genre == "contract" else (EMAIL_SYSTEM, EMAIL_USER)
        fb = ""
        best = None
        attempts = 0
        row_paid = row_list = 0.0
        for attempt in range(max_retries + 1):
            attempts += 1
            max_tok = int(len(body) / 4 * 1.8) + 200
            async with sem:
                text, paid, listed, *_ = await client.complete(system, tmpl.format(body=body, feedback=fb), max_tokens=max_tok,
                                                              cache_key=f"ablation2-paraphrase-{genre}")
            row_paid += paid
            row_list += listed
            text = re.sub(r"^</?(excerpt|message_body)>\s*|\s*</?(excerpt|message_body)>$", "", text).strip()
            c = check(body, text, genre)
            if best is None or (c["ok"] and not best[1]["ok"]) or (not best[1]["ok"] and c["caps_recall"] >= best[1]["caps_recall"] and c["numbers_ok"] >= best[1]["numbers_ok"]):
                best = (text, c)
            if c["ok"]:
                break
            fb = _feedback(c)
        text, c = best
        rec = {"id": r["id"], "text": (head + "\n\n" + text) if head else text, "check": c, "attempts": attempts, "ok": c["ok"],
               "cost_usd": round(row_paid, 6), "list_usd": round(row_list, 6), "model": spec.model_id, "orig_chars": len(body), "para_chars": len(text)}
        async with lock:
            cache[r["id"]] = rec
            with cache_path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            spent["paid"] += row_paid
            spent["list"] += row_list
            spent["calls"] += attempts

    try:
        await asyncio.gather(*(one(r) for r in todo))
    finally:
        await client.aclose()
    out = []
    for r in rows:
        c = cache[r["id"]]
        out.append({**r, "text": c["text"], "meta": {**(r.get("meta") or {}), "paraphrase_ok": c["ok"], "paraphrase_attempts": c["attempts"],
                                                      "paraphrase_ratio": c["check"]["ratio"], "caps_recall": c["check"]["caps_recall"]}})
    recs = [cache[r["id"]] for r in rows]
    stats = {"n": len(rows), "new": len(todo), "ok": sum(1 for x in recs if x["ok"]), "numbers_ok": sum(1 for x in recs if x["check"]["numbers_ok"]),
             "quotes_ok": sum(1 for x in recs if x["check"]["quotes_ok"]), "retried": sum(1 for x in recs if x["attempts"] > 1),
             "caps_recall_mean": round(sum(x["check"]["caps_recall"] for x in recs) / max(1, len(recs)), 3),
             "ratio_mean": round(sum(x["check"]["ratio"] for x in recs) / max(1, len(recs)), 3),
             "paid_usd_total": round(sum(x["cost_usd"] for x in recs), 4), "list_usd_total": round(sum(x["list_usd"] for x in recs), 4),
             "paid_usd_this_run": round(spent["paid"], 4), "calls_this_run": spent["calls"], "seconds": round(time.time() - t0)}
    log(f"paraphrase {genre}: {stats['n']} docs ({stats['new']} new), checks ok {stats['ok']}/{stats['n']}, numbers ok {stats['numbers_ok']}, "
        f"retried {stats['retried']}, caps recall {stats['caps_recall_mean']}, ratio {stats['ratio_mean']}; paid ${spent['paid']:.3f} this run "
        f"(${stats['paid_usd_total']:.3f} total)")
    return out, stats


# ------------------------------------------------------------------------------------------------ fidelity judge

JUDGE_SYSTEM = "You are a contracts lawyer comparing two versions of the same clause. Answer in JSON only."
JUDGE_USER = (
    "Compare the ORIGINAL and the REWRITE. List every difference in legal content: an obligation, right, condition, exception or remedy "
    "added, removed or changed; a party swapped; a number, amount, date or period changed; a defined term altered; a clause or cross-reference "
    "dropped. Ignore wording, sentence order and style. Reply with JSON only: {{\"equivalent\": true|false, \"differences\": [\"...\"]}} "
    "where \"equivalent\" is true when the two texts impose identical legal content.\n\n<original>\n{orig}\n</original>\n\n<rewrite>\n{para}\n</rewrite>"
)
JUDGE_EMAIL_SYSTEM = "You are an editor comparing two versions of the same message. Answer in JSON only."
JUDGE_EMAIL_USER = (
    "Compare the ORIGINAL and the REWRITE. List every difference in content: a fact, person, number, date, request, decision or attitude "
    "added, removed or changed. Ignore wording, sentence order and style. Reply with JSON only: {{\"equivalent\": true|false, \"differences\": [\"...\"]}}."
    "\n\n<original>\n{orig}\n</original>\n\n<rewrite>\n{para}\n</rewrite>"
)


async def fidelity_judge(pairs: list[tuple[str, str, str]], genre: str, out_path: Path, model: str = "gpt-5.6-terra", concurrency: int = 8, log=print) -> dict:
    """pairs: (id, original body, paraphrased body). Resumable JSONL at out_path. Returns summary."""
    done = _load_cache(out_path)
    spec = MODELS[model]
    client = FlexText(spec)
    sem = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    spent = [0.0]
    system, tmpl = (JUDGE_SYSTEM, JUDGE_USER) if genre == "contract" else (JUDGE_EMAIL_SYSTEM, JUDGE_EMAIL_USER)

    async def one(i, o, p):
        if i in done:
            return
        async with sem:
            text, paid, listed, *_ = await client.complete(system, tmpl.format(orig=o, para=p), max_tokens=400, cache_key=f"ablation2-judge-{genre}")
        m = re.search(r"\{.*\}", text, re.S)
        try:
            j = json.loads(m.group(0)) if m else {}
        except ValueError:
            j = {}
        rec = {"id": i, "model": spec.model_id, "equivalent": bool(j.get("equivalent", False)), "differences": j.get("differences", [])[:8] if isinstance(j.get("differences"), list) else [],
               "parsed": bool(m and j), "raw": text[:600], "cost_usd": round(paid, 6), "list_usd": round(listed, 6)}
        async with lock:
            done[i] = rec
            with out_path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            spent[0] += paid

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        await asyncio.gather(*(one(i, o, p) for i, o, p in pairs))
    finally:
        await client.aclose()
    recs = [done[i] for i, _, _ in pairs if i in done]
    summ = {"n": len(recs), "equivalent": sum(1 for r in recs if r["equivalent"]), "parsed": sum(1 for r in recs if r["parsed"]),
            "paid_usd_total": round(sum(r["cost_usd"] for r in recs), 4), "paid_usd_this_run": round(spent[0], 4), "model": spec.model_id,
            "examples_not_equivalent": [{"id": r["id"], "differences": r["differences"][:3]} for r in recs if not r["equivalent"]][:8]}
    log(f"fidelity judge ({genre}, {model}): {summ['equivalent']}/{summ['n']} judged equivalent; paid ${spent[0]:.3f} this run")
    return summ


# ------------------------------------------------------------------------------------------------ memorisation probe

MEMO_MODELS = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]


def contract_windows(by_contract: dict[int, list[dict]], variants: dict[str, dict[str, str]], per_contract: int = 2) -> list[dict]:
    """Up to `per_contract` windows per contract: excerpts with a long enough body, picked at ~30% and ~70% of the contract.
    variants: name -> {doc_id: text} for 'renamed' and 'paraphrased'. Returns items with gold target = ORIGINAL continuation and
    per-variant prefix + own target."""
    from ..contam.build import make_verbatim_item  # noqa: PLC0415  (read-only import)

    items = []
    for ci, docs in sorted(by_contract.items()):
        docs = sorted(docs, key=lambda d: d["meta"]["para_idx"])
        cands = []
        for d in docs:
            it = make_verbatim_item({"id": d["id"], "text": d["text"]}, "cuad")
            if it:
                cands.append((d, it))
        if not cands:
            continue
        picks = []
        for frac in ([0.3, 0.7] if per_contract >= 2 else [0.5])[:per_contract]:
            j = min(len(cands) - 1, int(frac * len(cands)))
            # nearest unused candidate
            order = sorted(range(len(cands)), key=lambda k: abs(k - j))
            for k in order:
                if k not in picks:
                    picks.append(k)
                    break
        for k in picks:
            d, it = cands[k]
            rec = {"contract_idx": ci, "doc_id": d["id"], "original": {"prefix": it["gold"]["prefix"], "target": it["gold"]["target"]},
                   "system": it["system"], "user_template": it["user"].replace(it["gold"]["prefix"], "{prefix}"), "variants": {}}
            for vname, texts in variants.items():
                if d["id"] not in texts:
                    continue
                vit = make_verbatim_item({"id": d["id"], "text": texts[d["id"]]}, "cuad")
                if vit:
                    rec["variants"][vname] = {"prefix": vit["gold"]["prefix"], "target": vit["gold"]["target"]}
            items.append(rec)
    return items


async def memo_probe(items: list[dict], out_path: Path, models: list[str] = MEMO_MODELS, variants=("original", "renamed", "paraphrased"),
                     concurrency: int = 8, log=print) -> list[dict]:
    """Ask each model to continue each window variant; score the continuation against the original target and the variant's own target.
    Resumable JSONL at out_path keyed (model, doc_id, variant)."""
    from ..contam.score import score_verbatim  # noqa: PLC0415  (read-only import)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["model"], r["doc_id"], r["variant"]) for r in (json.loads(l) for l in out_path.read_text().split("\n") if l.strip())} if out_path.exists() else set()
    lock = asyncio.Lock()
    spent: Counter = Counter()

    async def run_model(m: str):
        client = FlexText(MODELS[m])
        sem = asyncio.Semaphore(concurrency)

        async def one(it: dict, v: str):
            if (m, it["doc_id"], v) in done:
                return
            g = it["original"] if v == "original" else it["variants"].get(v)
            if g is None:
                return
            async with sem:
                text, paid, listed, *_ = await client.complete(it["system"], it["user_template"].format(prefix=g["prefix"]), max_tokens=160,
                                                              cache_key=f"ablation2-memo-{m}")
            s_orig = score_verbatim({"gold": {"target": it["original"]["target"], "prefix": g["prefix"]}}, text)
            s_own = score_verbatim({"gold": {"target": g["target"], "prefix": g["prefix"]}}, text)
            rec = {"model": m, "doc_id": it["doc_id"], "contract_idx": it["contract_idx"], "variant": v, "response": text,
                   "vs_original": s_orig, "vs_own": s_own, "cost_usd": round(paid, 6), "list_usd": round(listed, 6)}
            async with lock:
                with out_path.open("a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                spent[m] += paid

        try:
            await asyncio.gather(*(one(it, v) for it in items for v in variants))
        finally:
            await client.aclose()

    await asyncio.gather(*(run_model(m) for m in models))
    recs = [json.loads(l) for l in out_path.read_text().split("\n") if l.strip()]
    log(f"memo probe: {len(recs)} responses on file; paid this run " + ", ".join(f"{m} ${spent[m]:.3f}" for m in models) + f" (${sum(spent.values()):.3f})")
    return recs


def memo_summary(recs: list[dict]) -> dict:
    """Per model × variant: mean LCS-F1 vs the original continuation and vs the variant's own, share with a ≥ 15-word run, novel ≥ 8;
    and per contract × model the original-variant LCS-F1 (the memorisation dose)."""
    out: dict = {"by_model_variant": {}, "dose": {}}
    by = Counter()
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in recs:
        groups.setdefault((r["model"], r["variant"]), []).append(r)
    for (m, v), rs in sorted(groups.items()):
        ans = [r for r in rs if not r["vs_original"]["refusal"]]
        f = lambda key, fld: (sum(r[key][fld] for r in ans) / len(ans)) if ans else None  # noqa: E731
        out["by_model_variant"].setdefault(m, {})[v] = {
            "n": len(rs), "answered": len(ans), "lcs_f_vs_original": f("vs_original", "lcs_f"), "lcs_f_vs_own": f("vs_own", "lcs_f"),
            "max_run_vs_original": f("vs_original", "max_run"), "share_run15_vs_original": (sum(1 for r in ans if r["vs_original"]["max_run"] >= 15) / len(ans)) if ans else None,
            "share_novel8_vs_original": (sum(1 for r in ans if r["vs_original"]["novel_run"] >= 8) / len(ans)) if ans else None,
            "share_run15_vs_own": (sum(1 for r in ans if r["vs_own"]["max_run"] >= 15) / len(ans)) if ans else None,
        }
    dose: dict[str, dict[int, list[float]]] = {}
    for r in recs:
        if r["variant"] == "original" and not r["vs_original"]["refusal"]:
            dose.setdefault(r["model"], {}).setdefault(r["contract_idx"], []).append(r["vs_original"]["lcs_f"])
    out["dose"] = {m: {str(ci): round(sum(v) / len(v), 4) for ci, v in d.items()} for m, d in dose.items()}
    # pooled dose = mean over models
    pooled: dict[int, list[float]] = {}
    for m, d in dose.items():
        for ci, v in d.items():
            pooled.setdefault(ci, []).append(sum(v) / len(v))
    out["dose"]["pooled"] = {str(ci): round(sum(v) / len(v), 4) for ci, v in pooled.items()}
    return out

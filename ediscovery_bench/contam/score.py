"""Score the probe results: results/contam/summary.json and results/contam/REPORT.md."""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .boilerplate import REASON_LABEL, CorpusIndex, boilerplate_reasons
from .build import CORPORA, OUT_DIR, UNKNOWN_MARKERS
from .run import RESULTS_DIR, load_results

TOK_RE = re.compile(r"[a-z0-9]+")
# Refusal detection (verbatim probe). A refusal is a response that OPENS with a first-person inability / unwillingness
# ("I can't", "I'm sorry, but I cannot", "I'm not able to", "As an AI") AND names what is being withheld within its first
# 30 words ("provide the continuation", "reproduce", "reconstruct", "access"...). Anchoring at the start and requiring the
# object avoids the two failure modes of the old substring test: a genuine continuation that happens to contain "I'm sorry"
# or "I apologize for missing the call" is not a refusal, and a refusal that goes on to offer a summary (50-70 words) is.
# Apostrophes are matched straight or curly: every GPT-5.6 refusal in the data uses U+2019 ("I can’t"), which the old
# pattern "can't" never matched.
REFUSAL_HEAD_WORDS = 30
REFUSAL_OPEN_RE = re.compile(
    r"^\W*(?:(?:i['’]m |i am )?sorry[,.!\u2014-]*\s*(?:but )?|unfortunately,?\s*)?"
    r"(?:i\s*(?:can['’]?t|cannot|can not|won['’]t|will not|do not have access|don['’]t have access|do not have the|don['’]t have the"
    r"|am not able to|['’]m not able to|am unable to|['’]m unable to|am not going to|['’]m not going to)"
    r"|as an ai\b|i['’]m sorry,? (?:but )?(?:that|this) (?:is|isn['’]t) )",
    re.I,
)
REFUSAL_OBJ_RE = re.compile(
    r"\b(?:provide|providing|reproduce|reproducing|reconstruct|continue|continuation|complete|recall|generate|share|produce"
    r"|write|recreate|retrieve|supply|output|quote|access|help with|verbatim|fulfil|fulfill|assist with|comply)\b",
    re.I,
)
REFUSAL_KINDS = (  # why the model says it is refusing; "other" when no reason is given in the head
    ("private", re.compile(r"private|non-?user-?provided|not user-provided|personal|confidential|redacted|memori[sz]ation", re.I)),
    ("copyright", re.compile(r"copyright", re.I)),
)
REFUSAL_KIND_LABEL = {"private": "private / non-user-provided text", "copyright": "copyrighted text", "other": "no reason given"}


def detect_refusal(resp: str) -> str | None:
    """Return the refusal kind ('private' | 'copyright' | 'other') if the response opens with a refusal, else None."""
    head = " ".join(resp.split()[:REFUSAL_HEAD_WORDS])
    if not (REFUSAL_OPEN_RE.search(head) and REFUSAL_OBJ_RE.search(head)):
        return None
    for kind, rx in REFUSAL_KINDS:
        if rx.search(head):
            return kind
    return "other"
# Spectrum: real corpora, then the negative control (Veridian), then the positive controls (canon, titanic).
CORPUS_ORDER = ["enron", "jebbush", "mnk", "endo", "cuad", "veridian", "canon", "titanic"]
ENTITY_ORDER = ["enron", "jebbush", "mnk", "endo", "veridian", "canon"]
LABEL_ORDER = ["enron", "jebbush", "mnk", "endo", "veridian", "titanic"]
CONTROL = "veridian"


def toks(s: str) -> list[str]:
    return TOK_RE.findall(s.lower())


# ------------------------------------------------------------------------------------------------ verbatim

def lcs_len(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def common_runs(a: list[str], b: list[str]) -> list[tuple[int, int, int]]:
    """Maximal common contiguous runs as (length, start_in_a, start_in_b)."""
    n, m = len(a), len(b)
    prev = [0] * (m + 1)
    runs = []
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if i == n or j == m or a[i] != b[j]:  # run cannot extend: maximal
                    L = cur[j]
                    runs.append((L, i - L, j - L))
        prev = cur
    return runs


def score_verbatim(item: dict, resp: str) -> dict:
    target = toks(item["gold"]["target"])
    prefix = toks(item["gold"]["prefix"])
    gen_all = toks(resp)
    gen = gen_all[: len(target) + 5]
    kind = detect_refusal(resp)
    refusal = kind is not None
    if refusal or not gen:
        # an empty response is scored 0 but is not a refusal: it is recorded as refusal_kind "empty" so it can be audited
        return {"lcs_f": 0.0, "max_run": 0, "novel_run": 0, "refusal": refusal, "refusal_kind": kind or "empty", "gen_words": len(gen_all)}
    L = lcs_len(gen, target)
    p, r = L / len(gen), L / len(target)
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    runs = common_runs(gen, target)
    max_run = max((x[0] for x in runs), default=0)
    # novelty is number-blind: "vs. budget benchmark of 1,224 TRx" after "vs. budget benchmark of 650 TRx" in the prompt is a repeated
    # template with a new figure, not a remembered sentence, so digits are masked before the 5-gram comparison
    nb = lambda t: "#" if t.isdigit() else t  # noqa: E731
    prefix_5g = {tuple(map(nb, prefix[i:i + 5])) for i in range(len(prefix) - 4)}
    novel = 0
    for L_, _, j in runs:
        seg = [nb(t) for t in target[j:j + L_]]
        if L_ >= 5 and any(tuple(seg[k:k + 5]) not in prefix_5g for k in range(L_ - 4)):
            novel = max(novel, L_)
    return {"lcs_f": round(f, 4), "max_run": max_run, "novel_run": novel, "refusal": False, "refusal_kind": None, "gen_words": len(gen_all)}


# ------------------------------------------------------------------------------------------------ entities

def is_unknown(resp: str) -> bool:
    s = resp.strip().lower()
    return s.startswith("unknown") or any(m in s for m in UNKNOWN_MARKERS)


def score_entity_recall(item: dict, resp: str) -> dict:
    s = resp.lower()
    unknown = is_unknown(resp)
    hit = (not unknown) and any(k in s for k in item["gold"]["org_keywords"])
    # a hedged mention still counts as a hit only if the org is named; UNKNOWN+org ("unknown, possibly Enron") counts as hedge
    hedge_hit = unknown and any(k in s for k in item["gold"]["org_keywords"])
    return {"hit": hit, "unknown": unknown and not hedge_hit, "hedge_hit": hedge_hit, "other": (not hit) and (not unknown) and (not hedge_hit)}


def parse_yes_no(resp: str) -> str:
    s = resp.strip().lower().strip(".!\"'* ")
    first = re.split(r"[\s,.:;]+", s)[0] if s else ""
    if first in ("yes", "no", "unknown"):
        return first
    if s.startswith("yes"):
        return "yes"
    if s.startswith("no"):
        return "no"
    return "unknown"


def parse_relevance(resp: str, vocab: dict | None = None) -> str:
    s = resp.strip().lower().strip(".!\"'* ")
    if vocab:  # e.g. {"relevant": "survived", "not_relevant": "died"}
        neg, pos = vocab["not_relevant"].lower(), vocab["relevant"].lower()
        if s.startswith(neg) or "did not survive" in s or "didn't survive" in s or "not survive" in s:
            return "not_relevant"
        if s.startswith(pos):
            return "relevant"
        return "unknown"
    if s.startswith("not") or "not_relevant" in s or "not relevant" in s or "non_relevant" in s or "irrelevant" in s:
        return "not_relevant"
    if s.startswith("relevant"):
        return "relevant"
    return "unknown"


# ------------------------------------------------------------------------------------------------ bench knowledge

def score_bench(item: dict, resp: str) -> dict:
    s = resp.lower()
    if item["gold"].get("control"):
        return {"confabulated": not is_unknown(resp), "score": None, "recovered": []}
    rec = [name for name, kws in item["gold"]["keys"] if any(k in s for k in kws)]
    return {"score": round(len(rec) / len(item["gold"]["keys"]), 3), "recovered": rec, "n_keys": len(item["gold"]["keys"]), "confabulated": None}


# ------------------------------------------------------------------------------------------------ stats

def boot_ci(x: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    if not x:
        return (float("nan"), float("nan"))
    a = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    means = rng.choice(a, size=(n, len(a)), replace=True).mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def boot_diff_ci(x: list[float], y: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    if not x or not y:
        return (float("nan"), float("nan"))
    a, b = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    rng = np.random.default_rng(seed)
    d = rng.choice(a, size=(n, len(a))).mean(axis=1) - rng.choice(b, size=(n, len(b))).mean(axis=1)
    return (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def mannwhitney_p(x: list[float], y: list[float]) -> float:
    try:
        from scipy.stats import mannwhitneyu

        if not x or not y or (len(set(x)) == 1 and len(set(y)) == 1 and x[0] == y[0]):
            return float("nan")
        return float(mannwhitneyu(x, y, alternative="greater").pvalue)
    except Exception:  # noqa: BLE001
        return float("nan")


def binom_p(k: int, n: int) -> float:
    try:
        from scipy.stats import binomtest

        return float(binomtest(k, n, 0.5, alternative="two-sided").pvalue) if n else float("nan")
    except Exception:  # noqa: BLE001
        return float("nan")


def dprime(hits: int, n_sig: int, fas: int, n_noise: int) -> float:
    from scipy.stats import norm

    if not n_sig or not n_noise:
        return float("nan")
    h = (hits + 0.5) / (n_sig + 1)
    f = (fas + 0.5) / (n_noise + 1)
    return float(norm.ppf(h) - norm.ppf(f))


# ------------------------------------------------------------------------------------------------ aggregate

def verbatim_boilerplate(items: dict[str, dict], log=print) -> tuple[dict[str, list[str]], dict[str, dict]]:
    """Run the boilerplate detector (boilerplate.py) over every verbatim item. Returns (item_id -> reasons that fired, per-corpus
    counts). Items whose true continuation is e-mail boilerplate (disclaimers, signatures, quoted headers, footers), degraded text
    or a template recurring across the corpus are not a test of memorisation and are excluded from the V statistics; the flag is
    kept per item so the review page can show them. The detector is the same one the builder uses, so a rebuilt probe set contains
    no flagged windows."""
    flags: dict[str, list[str]] = {}
    counts: dict[str, dict] = {}
    by_corpus: dict[str, list[dict]] = defaultdict(list)
    for it in items.values():
        if it["probe"] == "verbatim":
            by_corpus[it["corpus"]].append(it)
    for c in CORPUS_ORDER:
        its = by_corpus.get(c, [])
        if not its:
            continue
        df = CorpusIndex(c).lookup([i["gold"]["target"] for i in its] + [i["gold"]["prefix"][-400:] for i in its], log=log)
        reasons: Counter = Counter()
        excluded = []
        for it in its:
            rs = boilerplate_reasons(it["gold"]["prefix"], it["gold"]["target"], CORPORA[c]["kind"], df)
            flags[it["item_id"]] = rs
            if rs:
                excluded.append(it["item_id"])
                reasons[rs[0]] += 1
        counts[c] = {"n_items": len(its), "n_excluded": len(excluded), "n_kept": len(its) - len(excluded),
                     "by_reason": dict(reasons.most_common()), "excluded_ids": excluded}
        log(f"[boilerplate] {c}: {len(excluded)}/{len(its)} verbatim windows excluded" + (f" ({', '.join(f'{k} {v}' for k, v in reasons.most_common())})" if reasons else ""))
    return flags, counts


def verbatim_pool(items: dict[str, dict], bp_flags: dict[str, list[str]], log=print) -> tuple[dict[str, dict], dict[str, dict]]:
    """Stage 2 of the pool filter: the LLM screen (screen.py), read from its cache — no model calls here; `contam-build` screens new
    windows. Returns (item_id -> {pool, exclude_reason, screen_class, screen_reason}, per-corpus counts). A window is in the pool
    only if no boilerplate rule fired AND the screen judged it original_internal (after the anchor exemption: the canon and the
    Titanic rows are public text by design, so `public_reproduction` does not exclude them)."""
    from .screen import ANCHOR_EXEMPT, effective_class, load_screen, screen_key  # noqa: PLC0415

    cache = load_screen()
    flags: dict[str, dict] = {}
    counts: dict[str, dict] = {}
    by_corpus: dict[str, list[dict]] = defaultdict(list)
    for it in items.values():
        if it["probe"] == "verbatim":
            by_corpus[it["corpus"]].append(it)
    for c in CORPUS_ORDER:
        its = by_corpus.get(c, [])
        if not its:
            continue
        by_class: Counter = Counter()
        by_rule: Counter = Counter()
        excluded, unscreened = [], 0
        for it in its:
            row = cache.get(screen_key(it))
            cls = effective_class(row, c)
            raw_cls = row["class"] if row else None
            if row is None:
                unscreened += 1
            rs = bp_flags.get(it["item_id"], [])
            if rs:
                reason = f"boilerplate:{rs[0]}"
                by_class["boilerplate"] += 1
                by_rule[rs[0]] += 1
            elif cls and cls != "original_internal":
                reason = cls
                by_class[cls] += 1
            else:
                reason = None
                by_class["kept"] += 1
            if reason:
                excluded.append(it["item_id"])
            flags[it["item_id"]] = {"v_pool": "excluded" if reason else "kept", "v_exclude_reason": reason,
                                    "v_screen_class": raw_cls, "v_screen_reason": row.get("reason") if row else None,
                                    "v_screen_exempt": bool(row and raw_cls != cls)}
        n_rep = sum(1 for it in its if it.get("meta", {}).get("replacement"))
        counts[c] = {"n_candidates": len(its), "n_kept": by_class["kept"], "n_excluded": len(excluded), "by_class": dict(by_class),
                     "by_rule": dict(by_rule.most_common()), "excluded_ids": excluded, "n_replacements": n_rep, "n_unscreened": unscreened,
                     "screen_exempt": sorted(ANCHOR_EXEMPT.get(c, set()))}
        log(f"[v_pool] {c}: kept {by_class['kept']}/{len(its)} ({', '.join(f'{k} {v}' for k, v in by_class.items() if k != 'kept')})"
            + (f"; {unscreened} not yet screened" if unscreened else ""))
    return flags, counts


def score_all(models: list[str], probes_path: Path = OUT_DIR / "probes.jsonl", log=print) -> dict:
    from .matter import (MATTER_LABEL, MATTER_ORDER, MATTER_ROLE, parse_responsive, score_evidence_prior, score_matter_id,  # noqa: PLC0415
                         score_matter_recall, topic_sets)
    from .screen import CLASS_LABEL  # noqa: PLC0415
    items = {i["item_id"]: i for i in (json.loads(l) for l in probes_path.open())}
    bp_flags, bp_counts = verbatim_boilerplate(items, log=log)
    pool_flags, pool_counts = verbatim_pool(items, bp_flags, log=log)
    summary: dict = {"models": [], "corpora": {c: CORPORA[c]["label"] for c in CORPUS_ORDER}, "verbatim": {}, "entity_recall": {},
                     "entity_recog": {}, "bench_knowledge": {}, "label_recall": {}, "cost_usd": {}, "resolved_model": {},
                     "matters": {k: MATTER_LABEL[k] for k in MATTER_ORDER}, "matter_roles": MATTER_ROLE,
                     "matter_id": {}, "matter_recall": {}, "evidence_prior": {}, "metadata_relevance": {}, "classifier_models": [],
                     "v_excluded_boilerplate": bp_counts, "v_boilerplate_reasons": REASON_LABEL,
                     "v_pool": pool_counts, "v_screen_classes": CLASS_LABEL}
    per_item_rows: list[dict] = []
    # lower-cased judged documents per request set, loaded lazily (only if any evidence_prior result exists)
    sets_by_key: dict[tuple[str, str], dict] | None = None
    docs_lower: dict[tuple[str, str], list[tuple[str, bool]]] = {}

    def _sets():
        nonlocal sets_by_key
        if sets_by_key is None:
            log("loading judged documents for the evidence-prior scoring ...")
            sets_by_key = {(s["set"], s["key"]): s for s in topic_sets()}
            for k, s in sets_by_key.items():
                docs_lower[k] = [(t.lower(), r) for _, t, r in s["docs"]]
        return sets_by_key

    for m in models:
        res = load_results(m)
        if not res:
            log(f"[{m}] no results")
            continue
        # cost of the main battery only: Big Thorium items share the result files but are costed in bigthorium_summary.json
        summary["cost_usd"][m] = round(sum(r.get("cost_usd", 0) for k, r in res.items() if ":bigthorium" not in k), 4)  # Big Thorium probes are costed in their own summary
        summary["resolved_model"][m] = sorted({r.get("resolved_model", "") for r in res.values()})
        V: dict[str, list[dict]] = defaultdict(list)      # verbatim items in the pool (passed the boilerplate rules AND the LLM screen)
        VRULES: dict[str, list[dict]] = defaultdict(list)  # passed the rules only (the intermediate stage, kept for the record)
        VALL: dict[str, list[dict]] = defaultdict(list)   # every verbatim item (the pre-exclusion numbers are kept for the record)
        ER: dict[str, list[dict]] = defaultdict(list)
        EG: dict[str, list[dict]] = defaultdict(list)
        BK: dict[str, dict] = {}
        LR: dict[str, list[dict]] = defaultdict(list)
        MI: dict[str, dict] = {}
        MR: dict[str, dict] = {}
        EP: dict[str, list[dict]] = defaultdict(list)  # set -> per-request scores
        MD: dict[str, dict[str, dict]] = defaultdict(dict)  # set -> doc_id -> {headers: pred, subject: pred, gold, lexical, topic}
        for iid, r in res.items():
            it = items.get(iid)
            if not it:
                continue
            resp = r.get("response", "") or ""
            p, c = it["probe"], it["corpus"]
            if p == "matter_id":
                s = score_matter_id(it, resp)
                MI[it["meta"]["sketch"]] = {**s, "corpus": c, "kind": it["meta"]["kind"], "response": resp}
                per_item_rows.append({"model": m, "item_id": iid, "probe": p, "corpus": c, **{k: v for k, v in s.items()}})
                continue
            if p == "matter_recall":
                s = score_matter_recall(it, resp)
                MR[it["meta"]["matter"]] = {**s, "response": resp}
                per_item_rows.append({"model": m, "item_id": iid, "probe": p, "corpus": c, **{k: v for k, v in s.items() if k not in ("missed",)}})
                continue
            if p == "evidence_prior":
                key = (it["meta"]["set"], it["meta"]["key"])
                st = _sets().get(key)
                if st is None:
                    continue
                s = score_evidence_prior(it, resp, st, docs_lower[key])
                s.update({"key": it["meta"]["key"], "title": it["meta"]["title"], "scandal": it["meta"]["scandal"]})
                EP[it["meta"]["set"]].append(s)
                per_item_rows.append({"model": m, "item_id": iid, "probe": p, "corpus": c, **{k: v for k, v in s.items() if k not in ("top_terms", "named_terms")}})
                continue
            if p == "metadata_relevance":
                md = MD[it["meta"]["set"]].setdefault(it["meta"]["doc_id"] + ":" + it["meta"]["key"],
                                                      {"gold": it["gold"]["answer"], "lexical": it["gold"]["lexical"], "topic": it["meta"]["key"], "corpus": c})
                md[it["meta"]["condition"]] = parse_responsive(resp)
                continue
            if p == "verbatim":
                s = score_verbatim(it, resp)
                rs = bp_flags.get(iid, [])
                s.update(boilerplate=bool(rs), boilerplate_reason=(rs[0] if rs else None), boilerplate_reasons=rs, **pool_flags.get(iid, {}))
                VALL[c].append(s)
                if not rs:
                    VRULES[c].append(s)
                if s.get("v_pool") == "kept":
                    V[c].append(s)
            elif p == "entity_recall":
                s = score_entity_recall(it, resp)
                s["tier"] = it["meta"]["tier"]
                ER[c].append(s)
            elif p == "entity_recog":
                s = {"ans": parse_yes_no(resp), "asked_org": it["gold"]["asked_org"], "is_true": it["gold"]["is_true_org"], "tier": it["meta"]["tier"]}
                EG[c].append(s)
            elif p == "bench_knowledge":
                s = score_bench(it, resp)
                BK[it["meta"]["question"]] = {**s, "corpus": c, "response": resp}
            elif p == "label_recall":
                s = {"pred": parse_relevance(resp, it["gold"].get("vocab")), "gold": it["gold"]["answer"], "topic": it["meta"].get("topic") or it["meta"].get("question")}
                LR[c].append(s)
            else:
                continue
            per_item_rows.append({"model": m, "item_id": iid, "probe": p, "corpus": c, **{k: v for k, v in s.items() if k != "response"}})

        if MD and not (V or ER or EG or BK or LR or MI or MR or EP):
            # a classifier (Jev): it can only be posed M3, so it is reported there and nowhere else
            summary["classifier_models"].append(m)
            summary["metadata_relevance"][m] = _metadata_summary(MD)
            log(f"[{m}] scored (classifier): metadata {sum(len(v) for v in MD.values())}  ${summary['cost_usd'][m]}")
            continue
        summary["models"].append(m)

        # verbatim. Refusals ("I can't provide the continuation of a private e-mail") say something about the model's policy,
        # nothing about memorisation, so every headline number (LCS-F1, runs, Mann-Whitney vs the floor) is computed over the
        # ANSWERED items only, for the real corpora and the Veridian floor alike; the refusal rate is reported next to it and
        # the refusals-as-zero mean is kept as `lcs_f_mean_all` for comparison with the earlier convention.
        def _answered(ys: list[dict]) -> list[dict]:
            return [x for x in ys if not x["refusal"]]

        ctrl_ans = _answered(V.get(CONTROL, []))
        ctrl_f = [x["lcs_f"] for x in ctrl_ans]
        ctrl_run = [x["max_run"] for x in ctrl_ans]
        vb = {}
        for c in CORPUS_ORDER:
            xs = V.get(c, [])
            if not xs:
                continue
            ans = _answered(xs)
            f = [x["lcs_f"] for x in ans]
            runs = [x["max_run"] for x in ans]
            xa = VALL.get(c, [])
            xr = VRULES.get(c, [])

            def _headline(ys: list[dict]) -> dict:
                ya = _answered(ys)
                return {"n": len(ys), "n_answered": len(ya), "refusal_rate": round(float(np.mean([x["refusal"] for x in ys])), 3),
                        "lcs_f_mean": round(float(np.mean([x["lcs_f"] for x in ya])), 4),
                        "lcs_f_mean_all": round(float(np.mean([x["lcs_f"] for x in ys])), 4),
                        "max_run_mean": round(float(np.mean([x["max_run"] for x in ya])), 2),
                        "frac_run_ge8": round(float(np.mean([x["max_run"] >= 8 for x in ya])), 3),
                        "frac_run_ge15": round(float(np.mean([x["max_run"] >= 15 for x in ya])), 3),
                        "frac_novel_run_ge8": round(float(np.mean([x["novel_run"] >= 8 for x in ya])), 3)} if ya else {"n": len(ys), "n_answered": 0}

            if not ans:
                vb[c] = {"n": len(xs), "n_answered": 0, "n_refused": len(xs), "refusal_rate": 1.0, "n_total": len(xa)}
                continue
            vb[c] = {
                "n": len(xs), "n_answered": len(ans), "n_refused": len(xs) - len(ans),
                "n_excluded": len(xa) - len(xs), "n_excluded_boilerplate": len(xa) - len(xr), "n_total": len(xa),
                "unfiltered": _headline(xa),   # the same headline numbers over every window with a response, for the record
                "rules_only": _headline(xr),   # after the boilerplate rules, before the LLM screen
                "lcs_f_mean": round(float(np.mean(f)), 4), "lcs_f_ci": boot_ci(f),
                "lcs_f_mean_all": round(float(np.mean([x["lcs_f"] for x in xs])), 4),   # refusals counted as 0 (old convention)
                "lcs_f_median": round(float(np.median(f)), 4),
                "max_run_mean": round(float(np.mean(runs)), 2), "max_run_ci": boot_ci(runs),
                "frac_run_ge8": round(float(np.mean([x["max_run"] >= 8 for x in ans])), 3),
                "frac_run_ge15": round(float(np.mean([x["max_run"] >= 15 for x in ans])), 3),
                "frac_novel_run_ge8": round(float(np.mean([x["novel_run"] >= 8 for x in ans])), 3),
                "frac_lcs_f_ge50": round(float(np.mean([x["lcs_f"] >= 0.5 for x in ans])), 3),
                "refusal_rate": round(float(np.mean([x["refusal"] for x in xs])), 3),
                "refusal_kinds": dict(Counter(x["refusal_kind"] for x in xs if x["refusal"])),
                "n_empty": sum(1 for x in xs if x.get("refusal_kind") == "empty"),
                "vs_control": None if c == CONTROL else {
                    "lcs_f_diff": round(float(np.mean(f) - np.mean(ctrl_f)), 4) if ctrl_f else None,
                    "lcs_f_diff_ci": boot_diff_ci(f, ctrl_f),
                    "lcs_f_p_greater": mannwhitney_p(f, ctrl_f),
                    # the same test under the old convention (refusals scored 0 on both sides), kept so the effect of the choice is visible
                    "lcs_f_p_greater_all": mannwhitney_p([x["lcs_f"] for x in xs], [x["lcs_f"] for x in V.get(CONTROL, [])]),
                    "max_run_diff": round(float(np.mean(runs) - np.mean(ctrl_run)), 2) if ctrl_run else None,
                    "max_run_p_greater": mannwhitney_p(runs, ctrl_run),
                },
            }
        summary["verbatim"][m] = vb

        # entity recall
        er = {}
        for c in ENTITY_ORDER:
            xs = ER.get(c, [])
            if not xs:
                continue
            hits = [x["hit"] for x in xs]
            er[c] = {
                "n": len(xs), "hit_rate": round(float(np.mean(hits)), 3), "hit_ci": wilson(sum(hits), len(xs)),
                "unknown_rate": round(float(np.mean([x["unknown"] for x in xs])), 3),
                "hedge_hit_rate": round(float(np.mean([x["hedge_hit"] for x in xs])), 3),
                "other_rate": round(float(np.mean([x["other"] for x in xs])), 3),
                "by_tier": {
                    t: {"n": len(ts), "hit_rate": round(float(np.mean([x["hit"] for x in ts])), 3),
                        "unknown_rate": round(float(np.mean([x["unknown"] for x in ts])), 3)}
                    for t in ("top", "mid", "tail") if (ts := [x for x in xs if x["tier"] == t])
                },
            }
        summary["entity_recall"][m] = er

        # entity recognition
        eg = {}
        for c in ENTITY_ORDER:
            xs = EG.get(c, [])
            if not xs:
                continue
            sig = [x for x in xs if x["is_true"]]
            noise = [x for x in xs if not x["is_true"]]
            h = sum(x["ans"] == "yes" for x in sig)
            fa = sum(x["ans"] == "yes" for x in noise)
            eg[c] = {
                "n_names": len(sig), "hit_rate": round(h / len(sig), 3) if sig else None, "hit_ci": wilson(h, len(sig)),
                "fa_rate": round(fa / len(noise), 3) if noise else None, "fa_ci": wilson(fa, len(noise)),
                "dprime": round(dprime(h, len(sig), fa, len(noise)), 2),
                "unknown_rate_true_org": round(float(np.mean([x["ans"] == "unknown" for x in sig])), 3) if sig else None,
                "yes_rate_by_asked_org": {
                    o: round(float(np.mean([x["ans"] == "yes" for x in xs if x["asked_org"] == o])), 3) for o in ENTITY_ORDER
                },
                "hit_rate_by_tier": {
                    t: round(float(np.mean([x["ans"] == "yes" for x in sig if x["tier"] == t])), 3)
                    for t in ("top", "mid", "tail") if any(x["tier"] == t for x in sig)
                },
            }
        summary["entity_recog"][m] = eg
        summary["bench_knowledge"][m] = BK

        # label recall
        lr = {}
        for c in LABEL_ORDER:
            xs = LR.get(c, [])
            if not xs:
                continue
            answered = [x for x in xs if x["pred"] != "unknown"]
            k = sum(x["pred"] == x["gold"] for x in answered)
            # best accuracy any topic->label rule could reach on this sample (the prevalence confound's ceiling)
            by_topic: dict[str, list[str]] = defaultdict(list)
            for x in xs:
                by_topic[x["topic"]].append(x["gold"])
            topic_ceiling = sum(max(g.count("relevant"), g.count("not_relevant")) for g in by_topic.values()) / len(xs)
            lr[c] = {
                "n": len(xs), "answered": len(answered), "acc": round(k / len(answered), 3) if answered else None,
                "acc_ci": wilson(k, len(answered)), "p_vs_chance": binom_p(k, len(answered)),
                "pred_relevant_rate": round(float(np.mean([x["pred"] == "relevant" for x in answered])), 3) if answered else None,
                "topic_only_ceiling": round(topic_ceiling, 3),
            }
        summary["label_recall"][m] = lr

        # matter identification / recall
        summary["matter_id"][m] = MI
        summary["matter_recall"][m] = MR

        # evidence prior: per request set (enron_j, enron_k, mnk, veridian, jebbush) and per corpus
        ep: dict[str, dict] = {}
        for st, xs in EP.items():
            def _mean(k):
                v = [x[k] for x in xs if x.get(k) is not None]
                return round(float(np.mean(v)), 3) if v else None
            ep[st] = {
                "n_requests": len(xs), "parsed_rate": round(float(np.mean([x["parsed"] for x in xs])), 3),
                "novel_rate": _mean("novel_rate"), "n_novel_named_mean": _mean("n_novel_named"),
                "grounded_rate_named": _mean("grounded_rate_named"), "discriminative_rate_named": _mean("discriminative_rate_named"),
                "grounded_rate_generic": _mean("grounded_rate_generic"), "discriminative_rate_generic": _mean("discriminative_rate_generic"),
                "grounded_rate_all": _mean("grounded_rate_all"), "discriminative_rate_all": _mean("discriminative_rate_all"),
                "n_discriminative_named_total": int(sum(x["n_discriminative_named"] for x in xs)),
                "per_request": {x["key"]: {k: x[k] for k in ("title", "scandal", "n_terms", "n_novel", "n_novel_named", "grounded_rate_named",
                                                             "discriminative_rate_named", "grounded_rate_all", "discriminative_rate_all",
                                                             "n_discriminative_named", "top_terms", "named_terms", "note")} for x in xs},
            }
        summary["evidence_prior"][m] = ep

        # metadata-only relevance: paired headers vs subject-only, per set and per corpus
        summary["metadata_relevance"][m] = _metadata_summary(MD)

        log(f"[{m}] scored: verbatim {sum(len(v) for v in V.values())} in pool (+{sum(len(v) for v in VALL.values()) - sum(len(v) for v in V.values())} excluded windows scored for the record), "
            f"recall {sum(len(v) for v in ER.values())}, "
            f"recog {sum(len(v) for v in EG.values())}, bench {len(BK)}, labels {sum(len(v) for v in LR.values())}, "
            f"matter_id {len(MI)}, matter_recall {len(MR)}, evidence {sum(len(v) for v in EP.values())}, "
            f"metadata {sum(len(v) for v in MD.values())}  ${summary['cost_usd'][m]}")

    # Big Thorium (Relativity's public demo workspace; invented case) is probed by contam/bigthorium.py; fold it in as a corpus so
    # the ladder, the composite and every per-collection figure carry it beside Veridian
    from .bigthorium import merge_into_summary as _merge_bt  # noqa: PLC0415
    _merge_bt(summary, log=log)
    summary["ladder"] = _ladder_summary(summary)
    summary["composite"] = _composite_summary(summary)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=1, default=_json_default))
    with (RESULTS_DIR / "scored_items.jsonl").open("w") as f:
        for r in per_item_rows:
            f.write(json.dumps(r, default=_json_default) + "\n")
    (RESULTS_DIR / "REPORT.md").write_text(render_report(summary))
    log(f"wrote {RESULTS_DIR / 'summary.json'}, {RESULTS_DIR / 'REPORT.md'}")
    return summary


COMPOSITE_DATASETS = ["enron", "jebbush", "mnk", "endo", "cuad", "veridian", "bigthorium"]  # bigthorium only when its probes were run
COMPOSITE_CHANNELS = ["V", "E", "L", "B", "M0", "M1", "M2"]
COMPOSITE_DOC_CHANNELS = ["V", "E", "L", "B"]
COMPOSITE_CASE_CHANNELS = ["M0", "M1", "M2"]
# benchmark-knowledge probes that are lists of the benchmark's own topics / categories (oida_mnk asks about the archive, not topics)
_B_TOPICS = {"enron": ["legal09", "legal10"], "jebbush": ["trec2016"], "cuad": ["cuad"], "veridian": ["veridian"], "bigthorium": ["relativity_air_demo"]}
_M2_SETS = {"enron": ["enron_j", "enron_j_named", "enron_k"], "jebbush": ["jebbush"], "mnk": ["mnk"], "endo": ["endo"], "veridian": ["veridian"]}


def _pos(v, floor, ceil):
    """Position of v between floor (0) and ceiling (100), clipped. None if undefined."""
    if v is None or floor is None or ceil is None or ceil <= floor:
        return None
    return round(min(100.0, max(0.0, 100.0 * (v - floor) / (ceil - floor))), 1)


def _composite_summary(summary: dict) -> dict:
    """A 0-100 contamination score per dataset x model: each channel's headline metric is placed between the floor (Veridian) and a
    ceiling (canon for V/E, chance->Titanic for L, 0->1 for B, Microsoft for M1, the max observed dataset for M2; M0 is 0/100), and the
    available channels are averaged with equal weight."""
    V, EG, LR, BK = summary["verbatim"], summary["entity_recog"], summary["label_recall"], summary["bench_knowledge"]
    MI, MR, EP = summary.get("matter_id", {}), summary.get("matter_recall", {}), summary.get("evidence_prior", {})
    datasets = [d for d in COMPOSITE_DATASETS if d != "bigthorium" or any("bigthorium" in V.get(m, {}) for m in summary["models"])]
    out = {"datasets": datasets, "channels": COMPOSITE_CHANNELS, "doc_channels": COMPOSITE_DOC_CHANNELS,
           "case_channels": COMPOSITE_CASE_CHANNELS, "per_model": {}, "ranking": {}}
    for m in summary["models"]:
        v, eg, lr, bk, mi, mr, ep = V[m], EG[m], LR[m], BK[m], MI.get(m, {}), MR.get(m, {}), EP.get(m, {})
        m2_vals = {d: max(ep[s_]["n_discriminative_named_total"] for s_ in sets if s_ in ep) for d, sets in _M2_SETS.items() if any(s_ in ep for s_ in sets)}
        m2_ceil = max(m2_vals.values()) if m2_vals else None
        rows = {}
        for d in datasets:
            ch: dict[str, float | None] = {}
            raw: dict[str, float | None] = {}
            # V: LCS-F1 between Veridian and the founding documents
            raw["V"] = v.get(d, {}).get("lcs_f_mean")
            ch["V"] = _pos(raw["V"], v.get(CONTROL, {}).get("lcs_f_mean"), v.get("canon", {}).get("lcs_f_mean"))
            # E: recognition d' (hit rate if d' is missing) between Veridian and the framers
            if d in eg:
                key = "dprime" if eg[d].get("dprime") is not None and eg.get("canon", {}).get("dprime") is not None else "hit_rate"
                raw["E"] = eg[d].get(key)
                ch["E"] = _pos(raw["E"], eg.get(CONTROL, {}).get(key), eg.get("canon", {}).get(key))
            else:
                raw["E"] = ch["E"] = None
            # L: label accuracy between chance (50%, Veridian sits there by construction) and Titanic
            raw["L"] = lr.get(d, {}).get("acc")
            ch["L"] = _pos(raw["L"], 0.5, lr.get("titanic", {}).get("acc"))
            # B: share of the benchmark's own topics recited, 0 -> 1 (Veridian: 0 unless the model confabulated a description)
            if d in _B_TOPICS:
                qs = [bk[q] for q in _B_TOPICS[d] if q in bk]
                if d == CONTROL:
                    raw["B"] = 1.0 if any(q.get("confabulated") for q in qs) else (0.0 if qs else None)
                else:
                    sc = [q["score"] for q in qs if q.get("score") is not None]
                    raw["B"] = float(np.mean(sc)) if sc else None
                ch["B"] = _pos(raw["B"], 0.0, 1.0)
            else:
                raw["B"] = ch["B"] = None
            # M0: identified the matter from a pseudonymised complaint / nameless sketch (Veridian: any real "model" named counts as 0 knowledge)
            if d in mi:
                raw["M0"] = 1.0 if (mi[d].get("hit") and not mi[d].get("control")) else 0.0
                ch["M0"] = 100.0 * raw["M0"]
            else:
                raw["M0"] = ch["M0"] = None
            # M1: recall share between Veridian (unknown -> 0) and Microsoft
            if d in mr:
                raw["M1"] = mr[d].get("share") or 0.0
                ch["M1"] = _pos(raw["M1"], mr.get(CONTROL, {}).get("share") or 0.0, mr.get("microsoft", {}).get("share"))
            else:
                raw["M1"] = ch["M1"] = None
            # M2: discriminative named terms (max over the dataset's request sets) between Veridian and the largest observed set
            raw["M2"] = m2_vals.get(d)
            ch["M2"] = _pos(raw["M2"], m2_vals.get(CONTROL), m2_ceil) if raw["M2"] is not None else None
            avail = [x for x in ch.values() if x is not None]
            doc = [ch[c] for c in COMPOSITE_DOC_CHANNELS if ch.get(c) is not None]
            case = [ch[c] for c in COMPOSITE_CASE_CHANNELS if ch.get(c) is not None]
            rows[d] = {"channels": ch, "raw": raw, "n_channels": len(avail), "n_doc": len(doc), "n_case": len(case),
                       "doc_score": round(float(np.mean(doc)), 1) if doc else None,
                       "case_score": round(float(np.mean(case)), 1) if case else None,
                       "composite": round(float(np.mean(avail)), 1) if avail else None}
        out["per_model"][m] = rows
        out["ranking"][m] = sorted(datasets, key=lambda d: -(rows[d]["composite"] or 0))
    return out


def _ladder_summary(summary: dict) -> dict:
    """The ladder of real matters: per-rung metadata + Wikipedia footprint + each model's M0/M1 result, and the rank correlation
    between footprint and recall share across rungs (the study's matters included where they have an article)."""
    from .ladder import FAMILY_LABEL, FAMILY_ORDER, FOOTPRINT_CACHE, FOOTPRINT_PROXY, LADDER  # noqa: PLC0415
    from .matter import MATTER_LABEL, MATTER_ROLE  # noqa: PLC0415
    fp = json.loads(FOOTPRINT_CACHE.read_text()) if FOOTPRINT_CACHE.exists() else {}
    rungs: dict[str, dict] = {}
    for k, r in LADDER.items():
        rungs[k] = {"label": r["label"], "year": r["year"], "family": r["family"], "expected": r["expected"], "n_facts": len(r["rubric"]),
                    "footprint": fp.get(k, {}), "study": False, "note": r.get("note")}
    for k in ("veridian", "jebbush", "enron", "mnk", "endo", "microsoft"):
        if k not in MATTER_LABEL or not any(k in summary["matter_recall"].get(m, {}) for m in summary["models"]):
            continue  # a study matter with no results yet (e.g. endo before its corpus is built) does not get an empty rung
        rungs[k] = {"label": MATTER_LABEL[k], "year": {"veridian": 2026, "jebbush": 2007, "enron": 2001, "mnk": 2020, "endo": 2022, "microsoft": 2001}[k],
                    "family": {"veridian": "devices", "jebbush": "email", "enron": "accounting", "mnk": "opioids", "endo": "opioids", "microsoft": "landmark"}[k],
                    "expected": MATTER_ROLE.get(k, "study"), "n_facts": None, "footprint": fp.get(k, {}), "study": True}
    if any("bigthorium" in summary["matter_recall"].get(m, {}) for m in summary["models"]):
        rungs["bigthorium"] = {"label": "Big Thorium (Relativity demo)", "year": 2024, "family": "procurement",
                               "expected": "public-invented", "n_facts": None, "footprint": {"title": None, "views_12m": 0, "absent": True}, "study": True}
    for k, r in rungs.items():
        if k in FOOTPRINT_PROXY and r["footprint"].get("title"):
            r["footprint"] = {**r["footprint"], "proxy": FOOTPRINT_PROXY[k]}
    per_model: dict[str, dict] = {}
    for m in summary["models"]:
        MI, MR = summary["matter_id"].get(m, {}), summary["matter_recall"].get(m, {})
        per_model[m] = {}
        for k in rungs:
            mi, mr = MI.get(k), MR.get(k)
            if mi is None and mr is None:
                continue
            per_model[m][k] = {
                "id_hit": mi["hit"] if mi else None, "id_unknown": mi["unknown"] if mi else None, "id_first_line": mi["first_line"] if mi else None,
                # the ladder compares matters on facts the question did not state (share_beyond_prompt); share_all keeps the raw number
                "share": (mr.get("share_beyond_prompt") if mr else None), "n_hit": (mr.get("n_hit_beyond_prompt") if mr else None),
                "n": (mr.get("n_beyond_prompt") if mr else None), "share_all": (mr.get("share") if mr else None),
                "by_cat": (mr.get("by_cat") if mr else None), "unknown": (mr["unknown"] if mr else None), "n_words": (mr["n_words"] if mr else None),
                "missed": (mr.get("missed", [])[:6] if mr else None),
            }
    # rank correlation footprint (log views) vs recall share, over rungs with a rubric and an article, per model
    corr: dict[str, dict] = {}
    for m, pm in per_model.items():
        xs, ys = [], []
        for k, v in pm.items():
            f = rungs[k]["footprint"]
            if v["share"] is None or not f or not f.get("title"):
                continue
            xs.append(math.log10(1 + f.get("views_12m", 0)))
            ys.append(v["share"])
        if len(xs) >= 5:
            from scipy.stats import spearmanr  # noqa: PLC0415
            sr = spearmanr(xs, ys)
            corr[m] = {"n": len(xs), "spearman": round(float(sr.statistic), 3), "p": round(float(sr.pvalue), 4)}
    return {"rungs": rungs, "families": {k: FAMILY_LABEL[k] for k in FAMILY_ORDER}, "per_model": per_model, "corr_views_recall": corr,
            "footprint_window": next((v.get("window") for v in fp.values() if v.get("window")), None)}


def _metadata_summary(MD: dict[str, dict[str, dict]]) -> dict:
    """MD: set -> doc:key -> {gold, lexical, headers, subject, topic, corpus}. Paired stats per set (with per-request breakdown) and per corpus."""
    mdr: dict[str, dict] = {}
    for st, docs in MD.items():
        pairs = [d for d in docs.values() if "headers" in d and "subject" in d]
        if not pairs:
            continue
        mdr[st] = _metadata_stats(pairs)
        mdr[st]["corpus"] = pairs[0]["corpus"]
        mdr[st]["by_topic"] = {t: _metadata_stats([d for d in pairs if d["topic"] == t], light=True) for t in sorted({d["topic"] for d in pairs})}
    by_corpus: dict[str, list[dict]] = defaultdict(list)
    for st, docs in MD.items():
        for d in docs.values():
            if "headers" in d and "subject" in d:
                by_corpus[d["corpus"]].append(d)
    return {"by_set": mdr, "by_corpus": {c: _metadata_stats(ds) for c, ds in by_corpus.items()}}


def _metadata_stats(pairs: list[dict], light: bool = False) -> dict:
    """pairs: [{gold, lexical, headers, subject, ...}]. Accuracy per condition, paired delta with bootstrap CI, lexical baseline."""
    n = len(pairs)
    ch = [int(d["headers"] == d["gold"]) for d in pairs]
    cs = [int(d["subject"] == d["gold"]) for d in pairs]
    cl = [int(d["lexical"] == d["gold"]) for d in pairs]
    kh, ks, kl = sum(ch), sum(cs), sum(cl)
    out = {
        "n": n,
        "acc_headers": round(kh / n, 3), "acc_subject": round(ks / n, 3), "acc_lexical": round(kl / n, 3),
        "delta_people": round((kh - ks) / n, 3),
    }
    if light:
        return out
    diffs = [a - b for a, b in zip(ch, cs)]
    rng = np.random.default_rng(0)
    arr = np.array(diffs)
    boots = [float(np.mean(rng.choice(arr, size=n, replace=True))) for _ in range(2000)]
    out.update({
        "acc_headers_ci": wilson(kh, n), "acc_subject_ci": wilson(ks, n),
        "p_headers_vs_chance": binom_p(kh, n), "p_subject_vs_chance": binom_p(ks, n),
        "delta_people_ci": (round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)),
        "resp_rate_headers": round(float(np.mean([d["headers"] == "responsive" for d in pairs])), 3),
        "resp_rate_subject": round(float(np.mean([d["subject"] == "responsive" for d in pairs])), 3),
        "unknown_rate": round(float(np.mean([d["headers"] == "unknown" or d["subject"] == "unknown" for d in pairs])), 3),
        # where the people changed the call: subject-only wrong -> headers right, and the reverse
        "fixed_by_people": int(sum(1 for a, b in zip(ch, cs) if a and not b)),
        "broken_by_people": int(sum(1 for a, b in zip(ch, cs) if b and not a)),
    })
    return out


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, float) and math.isnan(o):
        return None
    return str(o)


# ------------------------------------------------------------------------------------------------ report

def _f(v, nd=2, pct=False):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    if pct:
        return f"{100 * v:.0f}%"
    return f"{v:.{nd}f}"


def _ci(ci, nd=2, pct=False):
    if not ci or ci[0] is None or (isinstance(ci[0], float) and math.isnan(ci[0])):
        return ""
    if pct:
        return f" [{100 * ci[0]:.0f}–{100 * ci[1]:.0f}]"
    return f" [{ci[0]:.{nd}f}–{ci[1]:.{nd}f}]"


def _stars(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ""
    return " ***" if p < 0.001 else " **" if p < 0.01 else " *" if p < 0.05 else ""


V_SHORT = {"enron": "Enron", "jebbush": "Jeb Bush", "mnk": "Mallinckrodt", "endo": "Endo", "cuad": "CUAD", "veridian": "Veridian", "canon": "canon", "titanic": "Titanic"}


def pool_counts_text(s: dict) -> list[str]:
    """Per-corpus 'Enron: 60 candidates, 35 kept (boilerplate 10, public text 15)' strings from summary['v_pool']."""
    pool = s.get("v_pool") or {}
    labels = {"boilerplate": "boilerplate rules", "public_reproduction": "public text", "template_boilerplate": "template (screen)",
              "low_information": "low information"}
    out = []
    for c, x in pool.items():
        ex = ", ".join(f"{labels.get(k, k)} {v}" for k, v in x["by_class"].items() if k != "kept")
        rep = f"; {x['n_replacements']} replacements" if x.get("n_replacements") else ""
        out.append(f"{V_SHORT.get(c, c)}: {x['n_candidates']} candidates, {x['n_kept']} kept" + (f" ({ex}{rep})" if ex or rep else ""))
    return out


def boilerplate_note(s: dict, md: bool = True) -> str:
    """One paragraph stating how the verbatim pool was filtered (boilerplate rules, then the LLM screen), with per-corpus counts from
    summary.json; shared by REPORT.md and the HTML write-ups so the numbers are never typed in."""
    pool = s.get("v_pool") or {}
    if not pool:
        return ""
    code = (lambda t: f"`{t}`") if md else (lambda t: f"<code>{t}</code>")
    n_rules = sum(x["by_class"].get("boilerplate", 0) for x in pool.values())
    n_screen = sum(v for x in pool.values() for k, v in x["by_class"].items() if k not in ("kept", "boilerplate"))
    n_all = sum(x["n_candidates"] for x in pool.values())
    exempt = [V_SHORT.get(c, c) for c, x in pool.items() if x.get("screen_exempt")]
    return ("Verbatim pool quality: a window is a fair test of memorisation only if its continuation is text that only someone who had seen this "
            "collection could produce. Two filters are applied before any V statistic. (1) Rules (" + code("ediscovery_bench/contam/boilerplate.py") +
            "): confidentiality / privilege disclaimers, signature and footer blocks, forwarded-message headers, unsubscribe footers, auto-replies and "
            "bounces, scanner notices, protective-order legends, degenerate repetition, key: value lists and tables, OCR garbage, openings with too little "
            "real content, and templates or duplicates recurring across the corpus (8-gram document frequency). (2) An LLM screen (" + code("ediscovery_bench/contam/screen.py") +
            ", GPT-5.6 Luna, temperature 0) reads prefix + true continuation and assigns one of four classes; only " + code("original_internal") +
            " windows are kept. It removes reproductions of public text inside the corpus (Federal Register notices, news and wire stories, newsletters, "
            "press releases, product labels, standard clauses) and low-information windows (header-only or garbled openings, continuations predictable "
            "from the prefix). " + (f"The {' and '.join(exempt)} anchors are public text by design and are exempt from the public-text class only. " if exempt else "") +
            f"Of {n_all} candidate windows, {n_rules} fail the rules and a further {n_screen} fail the screen. " + "; ".join(pool_counts_text(s)) +
            ". Excluded windows stay in the probe file and are scored for the record (" + code("unfiltered") + " and " + code("rules_only") +
            " blocks per corpus); per-item fields in " + code("scored_items.jsonl") + ": " + ", ".join(code(k) for k in ("v_pool", "v_exclude_reason", "v_screen_class", "v_screen_reason", "boilerplate", "boilerplate_reason")) + ".\n")


def render_report(s: dict) -> str:
    L: list[str] = []
    L.append("# Training-data contamination probe\n")
    L.append("Design: `design/06_contamination_probe.md`. Columns run from the real corpora through the two ends of the spectrum: "
             "**veridian** (synthetic, written 2026: the model can know nothing) is the negative control in every table, and the positive controls are "
             "**canon** (Federalist Papers / Constitution / Declaration; the framers as the cast; 20 Newsgroups as the benchmark) and "
             "**titanic** (the Kaggle train.csv: verbatim rows, and passenger -> Survived for label recall). "
             "Stars mark one-sided Mann-Whitney vs Veridian (verbatim) or two-sided binomial vs 50% (label recall): * p<0.05, ** p<0.01, *** p<0.001.\n")
    models = s["models"]
    L.append("Models: " + ", ".join(f"`{m}` ({', '.join(s['resolved_model'][m])})" for m in models) + ".  ")
    L.append("Cost: " + ", ".join(f"{m} ${s['cost_usd'][m]:.2f}" for m in models) + f"; total ${sum(s['cost_usd'].values()):.2f}.\n")

    # V
    L.append("## V. Verbatim memorisation: continue the document\n")
    L.append("Mean word-level LCS F1 between the model's ~60-word continuation and the true continuation (95% bootstrap CI). "
             "Then the share of documents where the continuation reproduces an exact run of ≥ 8 words of the original "
             "(`novel`: the run contains at least one 5-gram not present in the prompt, digits masked). Refusal rate in the last column set.\n")
    L.append(boilerplate_note(s))
    cols = [c for c in CORPUS_ORDER]
    L.append("| model | " + " | ".join(f"{c} LCS-F1" for c in cols) + " |")
    L.append("|---|" + "---|" * len(cols))
    for m in models:
        vb = s["verbatim"].get(m, {})
        cells = []
        for c in cols:
            x = vb.get(c)
            if not x:
                cells.append("–")
                continue
            st = _stars(x["vs_control"]["lcs_f_p_greater"]) if x.get("vs_control") else ""
            cells.append(f"{_f(x['lcs_f_mean'], 3)}{_ci(x['lcs_f_ci'], 3)}{st}")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("| model | " + " | ".join(f"{c} run≥8 / novel≥8 / run≥15" for c in cols) + " |")
    L.append("|---|" + "---|" * len(cols))
    for m in models:
        vb = s["verbatim"].get(m, {})
        cells = []
        for c in cols:
            x = vb.get(c)
            cells.append("–" if not x else f"{_f(x['frac_run_ge8'], pct=True)} / {_f(x['frac_novel_run_ge8'], pct=True)} / {_f(x['frac_run_ge15'], pct=True)}")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("| model | " + " | ".join(f"{c} mean longest run (words)" for c in cols) + " | refusals (" + "/".join(cols) + ") |")
    L.append("|---|" + "---|" * (len(cols) + 1))
    for m in models:
        vb = s["verbatim"].get(m, {})
        cells = []
        for c in cols:
            x = vb.get(c)
            st = _stars(x["vs_control"]["max_run_p_greater"]) if x and x.get("vs_control") else ""
            cells.append("–" if not x else f"{_f(x['max_run_mean'], 1)}{_ci(x['max_run_ci'], 1)}{st}")
        ref = "/".join(_f(vb[c]["refusal_rate"], pct=True) if c in vb else "–" for c in cols)
        L.append(f"| {m} | " + " | ".join(cells) + f" | {ref} |")
    L.append("")

    # E recall
    L.append("## E1. Entity recall: \"Who is {name}?\"\n")
    L.append("Share of 30 header names per corpus (10 most frequent, 10 from ranks 11-40, 10 from the tail) whose free-text answer names the "
             "corpus's organisation (Wilson 95% CI), then the share answered UNKNOWN. Veridian names are fictional: a hit is impossible, "
             "and a non-UNKNOWN answer is a confabulation. Per-tier hit rates in the second table (top / mid / tail).\n")
    L.append("| model | " + " | ".join(f"{c} hit (unknown)" for c in ENTITY_ORDER) + " |")
    L.append("|---|" + "---|" * len(ENTITY_ORDER))
    for m in models:
        er = s["entity_recall"].get(m, {})
        cells = []
        for c in ENTITY_ORDER:
            x = er.get(c)
            cells.append("–" if not x else f"{_f(x['hit_rate'], pct=True)}{_ci(x['hit_ci'], pct=True)} ({_f(x['unknown_rate'], pct=True)})")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("| model | " + " | ".join(f"{c} top / mid / tail" for c in ENTITY_ORDER) + " |")
    L.append("|---|" + "---|" * len(ENTITY_ORDER))
    for m in models:
        er = s["entity_recall"].get(m, {})
        cells = []
        for c in ENTITY_ORDER:
            x = er.get(c)
            cells.append("–" if not x else " / ".join(_f(x["by_tier"].get(t, {}).get("hit_rate"), pct=True) for t in ("top", "mid", "tail")))
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    # E recog
    L.append("## E2. Entity recognition: \"Was {name} affiliated with {org}?\"\n")
    L.append("Each name is asked against its own organisation and the three others. Hit rate = yes to the true organisation; "
             "FA = yes to a foil; d' = z(hit) − z(FA). For Veridian names every yes is a false alarm (hit rate shown is yes-to-Veridian).\n")
    L.append("| model | " + " | ".join(f"{c} hit / FA / d'" for c in ENTITY_ORDER) + " |")
    L.append("|---|" + "---|" * len(ENTITY_ORDER))
    for m in models:
        eg = s["entity_recog"].get(m, {})
        cells = []
        for c in ENTITY_ORDER:
            x = eg.get(c)
            cells.append("–" if not x else f"{_f(x['hit_rate'], pct=True)} / {_f(x['fa_rate'], pct=True)} / {_f(x['dprime'], 1)}")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("Hit rate by name tier (top / mid / tail):\n")
    L.append("| model | " + " | ".join(ENTITY_ORDER) + " |")
    L.append("|---|" + "---|" * len(ENTITY_ORDER))
    for m in models:
        eg = s["entity_recog"].get(m, {})
        cells = []
        for c in ENTITY_ORDER:
            x = eg.get(c)
            cells.append("–" if not x else " / ".join(_f(x["hit_rate_by_tier"].get(t), pct=True) for t in ("top", "mid", "tail")))
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    # B
    L.append("## B. Benchmark knowledge\n")
    L.append("Fraction of the true topic titles / categories recovered from memory. `veridian`: whether the model described the "
             "fictional matter as if real (confabulated) rather than saying it did not know.\n")
    qids = ["trec2016", "legal10", "legal09", "cuad", "oida_mnk", "oida_endo", "veridian", "newsgroups20"]
    L.append("| model | TREC 2016 topics (34) | TREC Legal 2010 (4) | TREC Legal 2009 (7) | CUAD categories (41) | OIDA Mallinckrodt (4 facts) | OIDA Endo (4 facts) | Veridian confabulated? | 20 Newsgroups (20; positive control) |")
    L.append("|---|" + "---|" * len(qids))
    for m in models:
        bk = s["bench_knowledge"].get(m, {})
        cells = []
        for q in qids:
            x = bk.get(q)
            if not x:
                cells.append("–")
            elif q == "veridian":
                cells.append("yes" if x.get("confabulated") else "no")
            else:
                cells.append(f"{_f(x['score'], pct=True)} ({len(x['recovered'])}/{x['n_keys']})")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    # L
    L.append("## L. Label recall: relevance judgment from document id alone\n")
    L.append("Accuracy on 100 (document, topic) pairs with no document text, balanced 50/50 within every topic so the topic named in the "
             "prompt carries no label information (`ceiling` = the best any topic-only rule could score on the sample); chance is 50%. "
             "Mallinckrodt and Veridian labels were never published and must sit at chance. `answered`: share that gave relevant / not_relevant rather than refusing.\n")
    L.append("| model | " + " | ".join(f"{c} acc (ceiling; answered)" for c in LABEL_ORDER) + " |")
    L.append("|---|" + "---|" * len(LABEL_ORDER))
    for m in models:
        lr = s["label_recall"].get(m, {})
        cells = []
        for c in LABEL_ORDER:
            x = lr.get(c)
            cells.append("–" if not x else f"{_f(x['acc'], pct=True)}{_ci(x['acc_ci'], pct=True)}{_stars(x['p_vs_chance'])} ({_f(x['topic_only_ceiling'], pct=True)}; {x['answered']}/{x['n']})")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    # ---- M: knowing the case -----------------------------------------------------------------------------------------
    from .matter import MATTER_LABEL, MATTER_ORDER  # noqa: PLC0415
    SET_LABEL = {"enron_j": "Enron · Complaint J topics (the real scandal; pseudonym)", "enron_j_named": "Enron · Complaint J topics (company named)",
                 "enron_k": "Enron · Complaint K topics (oil spill; not Enron's story)", "mnk": "Mallinckrodt", "endo": "Endo (held-out)", "veridian": "Veridian (synthetic)", "jebbush": "Jeb Bush"}
    SET_ORDER = ["veridian", "jebbush", "enron_k", "enron_j", "enron_j_named", "mnk", "endo"]

    L.append("## M0. Matter identification: does a de-identified matter get mapped to the real one?\n")
    L.append("The TREC Legal complaints (Volteron = Enron; Bleak Horizon = Deepwater Horizon) and short de-identified sketches of the other matters. "
             "`hit` = the response names the real company / person / case. Veridian is fictional; `template` lists any real matter the model claimed it was modelled on.\n")
    sk_order = ["veridian", "jebbush", "enron", "enron_k", "mnk", "endo", "microsoft"]
    L.append("| model | " + " | ".join(sk_order) + " |")
    L.append("|---|" + "---|" * len(sk_order))
    for m in models:
        mi = s["matter_id"].get(m, {})
        cells = []
        for k in sk_order:
            x = mi.get(k)
            if not x:
                cells.append("–")
            elif x["control"]:
                cells.append(("unknown" if x["unknown"] else "named a real matter") + (f" → {'; '.join(x['templates'])}" if x["templates"] else ""))
            else:
                cells.append("hit" if x["hit"] else ("unknown" if x["unknown"] else "miss"))
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    L.append("## M1. Matter recall: the factual record from the matter's name alone\n")
    L.append("Share of a hand-written fact checklist (parties, allegations, people, events, outcome) recovered; `beyond` restricts to facts the study's "
             "task context does not already state. Veridian: whether the model said it did not know (correct) or confabulated.\n")
    L.append("| model | " + " | ".join(f"{MATTER_LABEL[k]} all / beyond" for k in MATTER_ORDER) + " |")
    L.append("|---|" + "---|" * len(MATTER_ORDER))
    for m in models:
        mr = s["matter_recall"].get(m, {})
        cells = []
        for k in MATTER_ORDER:
            x = mr.get(k)
            if not x:
                cells.append("–")
            elif x["control"]:
                cells.append(("said unknown" if x["unknown"] else f"confabulated ({x['n_words']} words)") + (f"; template {'; '.join(x['templates'])}" if x["templates"] else ""))
            else:
                cells.append(f"{_f(x['share'], pct=True)} / {_f(x['share_beyond'], pct=True)} ({x['n_hit']}/{x['n']})")
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("By category (parties / allegations / people / events / outcome):\n")
    L.append("| model | " + " | ".join(MATTER_LABEL[k] for k in MATTER_ORDER if k != "veridian") + " |")
    L.append("|---|" + "---|" * (len(MATTER_ORDER) - 1))
    for m in models:
        mr = s["matter_recall"].get(m, {})
        cells = []
        for k in MATTER_ORDER:
            if k == "veridian":
                continue
            x = mr.get(k)
            cells.append("–" if not x else " / ".join(_f(x["by_cat"].get(c), pct=True) for c in ("parties", "allegations", "people", "events", "outcome")))
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L.append("")

    # ---- the ladder
    lad = s.get("ladder") or {}
    if lad.get("per_model"):
        L.append("## The ladder: real matters at graded public exposure (M0 + M1)\n")
        L.append("Calibration rungs between the fictional floor and the Microsoft ceiling, in families matching the corpora, plus two post-cutoff "
                 "controls. Footprint = English-Wikipedia article (12-month pageviews / language editions). M0: did the model name the matter from a "
                 "de-identified sketch (● yes, ○ named something else, ? said it could not tell). M1: share of the fact checklist recovered, counting "
                 "only facts the question did not itself state; `unk` = the answer opened by declining.\n")
        rungs, pmm = lad["rungs"], lad["per_model"]

        def _sk(kv):
            k, r = kv
            fp = r["footprint"]
            if r["expected"] == "floor":
                return (3, 0, k)
            if r["expected"] == "none":
                return (2, 0, k)
            return (0, -(fp.get("views_12m") or 0), k) if fp.get("title") else (1, 0, k)
        L.append("| matter | family | year | expected | footprint | " + " | ".join(f"{m} M0 / M1" for m in models) + " |")
        L.append("|---|---|---|---|---|" + "---|" * len(models))
        for k, r in sorted(rungs.items(), key=_sk):
            fp = r["footprint"]
            fcell = (f"{fp['title']}" + (f" ({fp['proxy']})" if fp.get("proxy") else "") + f": {fp.get('views_12m', 0):,} views / {fp.get('langs', 0)} langs") if fp.get("title") else ("fictional" if r["expected"] == "floor" else "no article")
            cells = []
            for m in models:
                x = pmm.get(m, {}).get(k)
                if not x:
                    cells.append("–")
                    continue
                idm = "●" if x.get("id_hit") else ("?" if x.get("id_unknown") else "○")
                sh = _f(x["share"], pct=True) if x.get("share") is not None else "–"
                cells.append(f"{idm} / {sh}" + (" unk" if x.get("unknown") else ""))
            L.append(f"| {'**' + r['label'] + '**' if r.get('study') else r['label']} | {lad['families'].get(r['family'], r['family']).split(' (')[0]} | {r['year']} | {r['expected']} | {fcell} | " + " | ".join(cells) + " |")
        L.append("")
        if lad.get("corr_views_recall"):
            L.append("Spearman rank correlation, log pageviews vs M1 share, over matters with an article: " + "; ".join(
                f"{m}: ρ = {c['spearman']:+.2f} (n = {c['n']}, p = {c['p']})" for m, c in lad["corr_views_recall"].items()) + "\n")

    L.append("## M2. Evidence prior: what the model expects to find before seeing a document\n")
    L.append("25 expected terms per request (people, organisations, code names, products, places, periods, keywords). Terms already in the matter context or request "
             "are discarded (`novel`). Of the novel *named* terms: `grounded` = appears in ≥ 2 judged documents; `discriminative` = grounded and at least twice as "
             "frequent among responsive documents as overall (lift ≥ 2). Named terms are the case-knowledge signal; generic keywords are shown for comparison.\n")
    L.append("| model | set | requests | novel named / request | grounded (named) | discriminative (named) | grounded (generic) | discriminative (generic) | discriminative named terms (total) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for m in models:
        ep = s["evidence_prior"].get(m, {})
        for st in SET_ORDER:
            x = ep.get(st)
            if not x:
                continue
            L.append(f"| {m} | {SET_LABEL[st]} | {x['n_requests']} | {_f(x['n_novel_named_mean'], 1)} | {_f(x['grounded_rate_named'], pct=True)} | "
                     f"{_f(x['discriminative_rate_named'], pct=True)} | {_f(x['grounded_rate_generic'], pct=True)} | {_f(x['discriminative_rate_generic'], pct=True)} | {x['n_discriminative_named_total']} |")
    L.append("")

    L.append("## M3. Metadata-only relevance: does knowing the people move the call?\n")
    L.append("Balanced responsive / non-responsive e-mails per request; the model sees the matter context, the request and only the header metadata. "
             "`headers` = Date, From, To, Cc, Subject; `subject` = Date and Subject only. `Δ people` = headers − subject (paired bootstrap 95% CI): the accuracy "
             "that seeing who sent and received the e-mail adds. `lexical` = a request-title keyword match on the subject line. Chance is 50%.\n")
    if s.get("classifier_models"):
        L.append("Classifier rows (" + ", ".join(f"`{m}`" for m in s["classifier_models"]) + ") saw the same context, request and header block through "
                 "the classifier API (Noul question, no criteria). Their vendor states they are not pre-trained on public text; that is a claim under test here, and a flat "
                 "Δ people is consistent with it without establishing it, since the LLMs show the same flatness.\n")
    L.append("| model | set | n | headers | subject | Δ people | lexical | fixed / broken by people |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m in models + list(s.get("classifier_models", [])):
        md = s["metadata_relevance"].get(m, {})
        for st in SET_ORDER:
            x = md.get("by_set", {}).get(st)
            if not x:
                continue
            L.append(f"| {m} | {SET_LABEL[st]} | {x['n']} | {_f(x['acc_headers'], pct=True)}{_ci(x['acc_headers_ci'], pct=True)}{_stars(x['p_headers_vs_chance'])} | "
                     f"{_f(x['acc_subject'], pct=True)}{_ci(x['acc_subject_ci'], pct=True)}{_stars(x['p_subject_vs_chance'])} | "
                     f"{'+' if x['delta_people'] > 0 else ''}{_f(x['delta_people'], pct=True)} [{_f(x['delta_people_ci'][0], pct=True)}, {_f(x['delta_people_ci'][1], pct=True)}] | "
                     f"{_f(x['acc_lexical'], pct=True)} | {x['fixed_by_people']} / {x['broken_by_people']} |")
    L.append("")

    # bench knowledge transcripts
    L.append("## Appendix: benchmark-knowledge answers\n")
    for m in models:
        bk = s["bench_knowledge"].get(m, {})
        for q in qids:
            x = bk.get(q)
            if not x:
                continue
            L.append(f"<details><summary><code>{m}</code> — {q}" + (f" — recovered {len(x['recovered'])}/{x['n_keys']}: {', '.join(x['recovered'])}" if x.get("recovered") else "") + "</summary>\n")
            L.append("```\n" + (x.get("response") or "").strip()[:3000] + "\n```\n</details>\n")
    L.append("## Appendix: matter identification and recall answers\n")
    for m in models:
        for k, x in s["matter_id"].get(m, {}).items():
            L.append(f"<details><summary><code>{m}</code> — matter_id {k} — {'hit' if x['hit'] else ('unknown' if x['unknown'] else 'no hit')}"
                     + (f" — template: {'; '.join(x['templates'])}" if x["templates"] else "") + "</summary>\n")
            L.append("```\n" + (x.get("response") or "").strip()[:2500] + "\n```\n</details>\n")
        for k, x in s["matter_recall"].get(m, {}).items():
            L.append(f"<details><summary><code>{m}</code> — matter_recall {k}" + (f" — {x['n_hit']}/{x['n']}; missed: {', '.join(x['missed'][:8])}" if x["n"] else "") + "</summary>\n")
            L.append("```\n" + (x.get("response") or "").strip()[:6000] + "\n```\n</details>\n")
    return "\n".join(L) + "\n"

"""Score every test -> results/jev_probe/summary.json. Pure function of the data and prediction files."""
from __future__ import annotations

import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from ..runner import job_path
from .common import (DATA, JEV, LLMS, LUNA, RESULTS, ROOT, SEED, T1_CARRIED_OVER, TERRA, bootstrap_ci, ledger_total, mann_whitney_p, mcnemar, paired_diff,
                     prediction_spend, read_jsonl, wilson)
from .items import BARE_TOKENS, MATTERS

POS = "responsive"
ALL_MODELS = [JEV] + LLMS


def _preds(test: str, model: str, tag: str) -> dict[tuple[str, str], dict]:
    p = job_path(RESULTS, test, "multi", model, tag)
    out = {}
    for r in read_jsonl(p):
        if r.get("error"):
            continue
        out[(r["doc_id"], r["question"])] = r
    return out


def _call(r: dict | None) -> bool | None:
    return None if r is None else (r["label"] == POS)


def _rate_block(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else float("nan"), "ci": [lo, hi]}


# ------------------------------------------------------------------------------------------------ T1

def _t1_pairs(matter: str) -> list[dict]:
    rows = read_jsonl(DATA / f"t1_{matter}.jsonl")
    by = defaultdict(dict)
    for r in rows:
        by[r["meta"]["pair"]][r["meta"]["condition"]] = r
    out = []
    for pair, d in sorted(by.items()):
        m = d["real"]["meta"]
        out.append({"pair": pair, "qid": m["qid"], "kind": m["kind"], "token": m["token"], "real_id": d["real"]["id"], "fake_id": d["fake"]["id"]})
    return out


def _paired_block(items: list[tuple[bool, bool, float, float]], seed: int = SEED) -> dict:
    """items: (call_real, call_fake, p_real, p_fake)."""
    if not items:
        return {"n": 0}
    yr = [1.0 if a else 0.0 for a, _, _, _ in items]
    yf = [1.0 if b else 0.0 for _, b, _, _ in items]
    d = paired_diff(yr, yf, seed=seed)
    b = sum(1 for a, bb, _, _ in items if a and not bb)
    c = sum(1 for a, bb, _, _ in items if not a and bb)
    dp = paired_diff([x for _, _, x, _ in items], [y for _, _, _, y in items], seed=seed)
    return {"n": len(items), "rate_real": sum(yr) / len(yr), "rate_fake": sum(yf) / len(yf), "diff": d["mean"], "diff_ci": d["ci"],
            "real_yes_fake_no": b, "real_no_fake_yes": c, "mcnemar_p": mcnemar(b, c), "mean_p_real": statistics.mean(x for _, _, x, _ in items),
            "mean_p_fake": statistics.mean(y for _, _, _, y in items), "dp": dp["mean"], "dp_ci": dp["ci"]}


def _contrast(sig: list[tuple], dec: list[tuple], n_boot: int = 2000, seed: int = SEED) -> dict:
    """(signal diff) - (decoy diff) with an independent-groups bootstrap: positive if knowledge moves calls in the expected directions."""
    if not sig or not dec:
        return {}
    rng = random.Random(seed)

    def diff(items):
        return sum((1 if a else 0) - (1 if b else 0) for a, b, _, _ in items) / len(items)

    bs = []
    for _ in range(n_boot):
        s = [sig[rng.randrange(len(sig))] for _ in sig]
        d = [dec[rng.randrange(len(dec))] for _ in dec]
        bs.append(diff(s) - diff(d))
    bs.sort()
    return {"value": diff(sig) - diff(dec), "ci": [bs[int(0.025 * n_boot)], bs[int(0.975 * n_boot) - 1]]}


def score_t1(test: str = "t1") -> dict:
    """`test` = "t1" (v2, token-free contexts) or "t1_v1_confounded" (the archived v1 run whose Mallinckrodt / Endo contexts named the products)."""
    out = {}
    for matter in MATTERS:
        pairs = _t1_pairs(matter)
        per_model = {}
        for model in ALL_MODELS:
            preds = _preds(test, model, matter)
            if not preds:
                continue
            sig, dec, by_token = [], [], defaultdict(list)
            for p in pairs:
                r, f = preds.get((p["real_id"], p["qid"])), preds.get((p["fake_id"], p["qid"]))
                if r is None or f is None:
                    continue
                item = (_call(r), _call(f), float(r["p_positive"]), float(f["p_positive"]))
                (sig if p["kind"] == "signal" else dec).append(item)
                by_token[p["token"]].append(item)
            per_model[model] = {"signal": _paired_block(sig), "decoy": _paired_block(dec), "contrast_signal_minus_decoy": _contrast(sig, dec),
                                "by_token": {t: {"n": len(v), "rate_real": sum(1 for a, _, _, _ in v if a) / len(v), "rate_fake": sum(1 for _, b, _, _ in v if b) / len(v),
                                                 "mean_p_real": statistics.mean(x for _, _, x, _ in v), "mean_p_fake": statistics.mean(y for _, _, _, y in v)}
                                             for t, v in sorted(by_token.items())}}
        out[matter] = {"n_pairs": len(pairs), "n_signal": sum(1 for p in pairs if p["kind"] == "signal"), "n_decoy": sum(1 for p in pairs if p["kind"] == "decoy"),
                       "models": per_model}
    return out


# ------------------------------------------------------------------------------------------------ bare-token

def score_bare() -> dict:
    docs = read_jsonl(DATA / "bt_docs.jsonl")
    out = {}
    for tag in ("aswritten", "named", "aswritten__enronctx", "named__enronctx"):
        preds = _preds("bt", JEV, tag)
        if not preds:
            continue
        cells = {}
        for cond in ("real", "fake"):
            rs = [preds.get((d["id"], "fas140")) for d in docs if d["meta"]["condition"] == cond]
            rs = [r for r in rs if r is not None]
            if not rs:
                continue
            blk = _rate_block([_call(r) for r in rs])
            blk["mean_p"] = statistics.mean(float(r["p_positive"]) for r in rs)
            blk["by_token"] = {}
            for tok in BARE_TOKENS:
                rt = [preds.get((d["id"], "fas140")) for d in docs if d["meta"]["condition"] == cond and d["meta"]["token"] == tok]
                rt = [r for r in rt if r is not None]
                if rt:
                    blk["by_token"][tok] = {"n": len(rt), "rate": sum(_call(r) for r in rt) / len(rt), "mean_p": statistics.mean(float(r["p_positive"]) for r in rt)}
            cells[cond] = blk
        # paired real-vs-fake by sentence x token
        items = []
        by = defaultdict(dict)
        for d in docs:
            r = preds.get((d["id"], "fas140"))
            if r is not None:
                by[d["meta"]["pair"]][d["meta"]["condition"]] = r
        for pair, dd in by.items():
            if "real" in dd and "fake" in dd:
                items.append((_call(dd["real"]), _call(dd["fake"]), float(dd["real"]["p_positive"]), float(dd["fake"]["p_positive"])))
        out[tag] = {"cells": cells, "paired": _paired_block(items)}
    return out


# ------------------------------------------------------------------------------------------------ T2

def score_t2() -> dict:
    out = {}
    for coll in ("enron", "jebbush", "veridian"):
        edited = [r for r in read_jsonl(DATA / f"t2_{coll}__edited.jsonl") if r["meta"].get("applied")]
        all_ed = read_jsonl(DATA / f"t2_{coll}__edited.jsonl")
        info = {"n_docs": len(read_jsonl(DATA / f"t2_{coll}.jsonl")), "n_edited": len(edited),
                "n_infeasible": sum(1 for r in all_ed if not r["meta"].get("feasible", True)), "n_failed": sum(1 for r in all_ed if r["meta"].get("feasible", True) and not r["meta"].get("applied")),
                "edit_chars_median": statistics.median(r["meta"]["edit_chars"] for r in edited) if edited else None,
                "doc_chars_median": statistics.median(len(r["text"]) for r in edited) if edited else None, "models": {}}
        if not edited:
            out[coll] = info
            continue
        qids = sorted({r["meta"]["target_qid"] for r in edited})
        for model in ALL_MODELS:
            po, pe = {}, {}
            for q in qids:
                po.update(_preds("t2", model, f"{coll}__orig__{q}"))
                pe.update(_preds("t2", model, f"{coll}__edited__{q}"))
            if not pe:
                continue
            rows = []
            for r in edited:
                q, old, new = r["meta"]["target_qid"], r["meta"]["old_label"], r["meta"]["new_label"]
                o, e = po.get((r["id"], q)), pe.get((r["id"], q))
                if e is None:
                    continue
                rows.append({"id": r["id"], "q": q, "old": old, "new": new, "orig_call": o["label"] if o else None, "edit_call": e["label"],
                             "p_orig": float(o["p_positive"]) if o else None, "p_edit": float(e["p_positive"]), "edit_chars": r["meta"]["edit_chars"]})
            if not rows:
                continue
            follow = [x["edit_call"] == x["old"] for x in rows]
            reads = [x["edit_call"] == x["new"] for x in rows]
            acc_orig = [x["orig_call"] == x["old"] for x in rows if x["orig_call"] is not None]
            cond = [x for x in rows if x["orig_call"] == x["old"]]
            blk = {"n": len(rows), "acc_original": _rate_block(acc_orig) if acc_orig else None, "label_following": _rate_block(follow), "reads_edit": _rate_block(reads),
                   "label_following_given_orig_correct": _rate_block([x["edit_call"] == x["old"] for x in cond]) if cond else None,
                   "by_direction": {}, "mean_abs_dp": statistics.mean(abs(x["p_edit"] - x["p_orig"]) for x in rows if x["p_orig"] is not None) if any(x["p_orig"] is not None for x in rows) else None}
            for d_old in (POS, "not_responsive"):
                sub = [x for x in rows if x["old"] == d_old]
                if sub:
                    blk["by_direction"][f"{d_old}->"] = {"n": len(sub), "label_following": _rate_block([x["edit_call"] == x["old"] for x in sub]),
                                                        "acc_original": _rate_block([x["orig_call"] == x["old"] for x in sub if x["orig_call"] is not None]) if any(x["orig_call"] for x in sub) else None}
            info["models"][model] = blk
        # verification by a second model
        pv = {}
        for q in qids:
            pv.update(_preds("t2", TERRA, f"{coll}__verify__{q}"))
        if pv:
            ok = [pv[(r["id"], r["meta"]["target_qid"])]["label"] == r["meta"]["new_label"] for r in edited if (r["id"], r["meta"]["target_qid"]) in pv]
            info["verify"] = {"model": TERRA, **_rate_block(ok)}
        out[coll] = info
    # contrast vs the Veridian calibration arm (independent bootstrap on label-following flags)
    out["_contrast_vs_veridian"] = {}
    for model in ALL_MODELS:
        v = out.get("veridian", {}).get("models", {}).get(model)
        if not v:
            continue
        for coll in ("enron", "jebbush"):
            c = out.get(coll, {}).get("models", {}).get(model)
            if not c:
                continue
            rng = random.Random(SEED)
            a = [1] * c["label_following"]["k"] + [0] * (c["label_following"]["n"] - c["label_following"]["k"])
            b = [1] * v["label_following"]["k"] + [0] * (v["label_following"]["n"] - v["label_following"]["k"])
            bs = sorted(statistics.mean(rng.choice(a) for _ in a) - statistics.mean(rng.choice(b) for _ in b) for _ in range(2000))
            out["_contrast_vs_veridian"][f"{model}/{coll}"] = {"diff": c["label_following"]["rate"] - v["label_following"]["rate"], "ci": [bs[50], bs[1949]]}
    return out


# ------------------------------------------------------------------------------------------------ T3

def score_t3() -> dict:
    out = {}
    per_corpus_dp: dict[str, list[float]] = {}
    for corpus in ("enron", "endo", "veridian"):
        para = {r["id"]: r for r in read_jsonl(DATA / f"t3_{corpus}__para.jsonl") if r["meta"].get("applied")}
        po, pp = _preds("t3", JEV, f"{corpus}__orig"), _preds("t3", JEV, f"{corpus}__para")
        if not pp:
            continue
        by_doc: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for (doc, q), e in pp.items():
            o = po.get((doc, q))
            if o is not None and doc in para:
                by_doc[doc].append((float(o["p_positive"]), float(e["p_positive"])))
        dps = [abs(a - b) for v in by_doc.values() for a, b in v]
        flips = [(a >= 0.5) != (b >= 0.5) for v in by_doc.values() for a, b in v]
        doc_flip = [any((a >= 0.5) != (b >= 0.5) for a, b in v) for v in by_doc.values()]
        doc_mean_dp = [statistics.mean(abs(a - b) for a, b in v) for v in by_doc.values()]
        sims = [para[d]["meta"]["similarity"] for d in by_doc]
        per_corpus_dp[corpus] = dps
        # similarity bands (paraphrase intensity) so corpora can be compared at equal distance
        bands = {}
        for lo, hi, name in ((0.0, 0.6, "<0.60"), (0.6, 0.75, "0.60-0.75"), (0.75, 1.01, ">=0.75")):
            ds = [d for d in by_doc if lo <= para[d]["meta"]["similarity"] < hi]
            if ds:
                bands[name] = {"n_docs": len(ds), "mean_abs_dp": statistics.mean(abs(a - b) for d in ds for a, b in by_doc[d]),
                               "flip_rate": statistics.mean((a >= 0.5) != (b >= 0.5) for d in ds for a, b in by_doc[d])}
        out[corpus] = {"n_docs": len(by_doc), "n_decisions": len(dps), "mean_abs_dp": statistics.mean(dps), "mean_abs_dp_ci": list(bootstrap_ci(doc_mean_dp)),
                       "median_abs_dp": statistics.median(dps), "p90_abs_dp": sorted(dps)[int(0.9 * len(dps))], "flip_rate": statistics.mean(flips),
                       "flip_rate_ci": list(bootstrap_ci([statistics.mean((a >= 0.5) != (b >= 0.5) for a, b in v) for v in by_doc.values()])),
                       "doc_flip_rate": _rate_block(doc_flip), "similarity_mean": statistics.mean(sims), "similarity_median": statistics.median(sims), "by_similarity": bands}
    if "veridian" in per_corpus_dp:
        for corpus in ("enron", "endo"):
            if corpus in per_corpus_dp:
                out[corpus]["mw_p_vs_veridian"] = mann_whitney_p(per_corpus_dp[corpus], per_corpus_dp["veridian"])
    return out


# ------------------------------------------------------------------------------------------------ T4 Enron

def _panel_label(calls: dict[str, str | None], need: int) -> str | None:
    vals = [v for v in calls.values() if v is not None]
    if len(vals) < need:
        return None
    c = Counter(vals)
    lab, n = c.most_common(1)[0]
    return lab if n == len(vals) else None  # unanimous among the panel members that answered


def score_t4_enron() -> dict:
    judged = read_jsonl(DATA / "t4_enron_judged.jsonl")
    unjudged = read_jsonl(DATA / "t4_enron_unjudged.jsonl")
    out: dict = {"n_judged": len(judged), "n_unjudged": len(unjudged)}
    if not unjudged:
        out["note"] = "unjudged sample not built (EDRM pool missing)"
    panel_models = [LUNA, TERRA]
    sides = {}
    for side, rows in (("judged", judged), ("unjudged", unjudged)):
        if not rows:
            continue
        jev = _preds("t4", JEV, f"enron__{side}")
        panels = {m: _preds("t4", m, f"enron__{side}") for m in panel_models}
        have_panel = all(panels[m] for m in panel_models)
        recs = []
        for r in rows:
            q = r["meta"]["topic_key"]
            j = jev.get((r["id"], q))
            if j is None:
                continue
            pl = _panel_label({m: (panels[m][(r["id"], q)]["label"] if (r["id"], q) in panels[m] else None) for m in panel_models}, len(panel_models)) if have_panel else None
            recs.append({"id": r["id"], "q": q, "jev": j["label"], "p": float(j["p_positive"]), "qrels": r["meta"].get("qrels_label"), "panel": pl,
                         "n_chars": len(r["text"]), "enriched": r["meta"].get("enriched")})
        blk: dict = {"n": len(recs), "jev_positive_rate": _rate_block([x["jev"] == POS for x in recs]), "panel_available": have_panel,
                     "n_chars_median": statistics.median(x["n_chars"] for x in recs) if recs else None}
        if side == "judged":
            blk["jev_acc_vs_qrels"] = _rate_block([x["jev"] == x["qrels"] for x in recs])
            blk["jev_acc_vs_qrels_by_gold"] = {g: _rate_block([x["jev"] == x["qrels"] for x in recs if x["qrels"] == g]) for g in (POS, "not_responsive")}
            blk["qrels_positive_rate"] = _rate_block([x["qrels"] == POS for x in recs])
        if have_panel:
            withp = [x for x in recs if x["panel"] is not None]
            blk["n_panel_unanimous"] = len(withp)
            blk["jev_agree_panel"] = _rate_block([x["jev"] == x["panel"] for x in withp])
            blk["jev_agree_panel_by_panel"] = {g: _rate_block([x["jev"] == x["panel"] for x in withp if x["panel"] == g]) for g in (POS, "not_responsive")}
            blk["panel_positive_rate"] = _rate_block([x["panel"] == POS for x in withp])
            if side == "judged":
                blk["panel_acc_vs_qrels"] = _rate_block([x["panel"] == x["qrels"] for x in withp])
            if side == "unjudged":
                enr = [x for x in withp if x["enriched"]]
                if enr:
                    blk["enriched_subset"] = {"n": len(enr), "jev_agree_panel": _rate_block([x["jev"] == x["panel"] for x in enr]), "panel_positive_rate": _rate_block([x["panel"] == POS for x in enr])}
        blk["_recs"] = recs
        sides[side] = blk
    # headline: accuracy difference (judged vs qrels) - (unjudged vs panel), independent bootstrap
    if "judged" in sides and "unjudged" in sides and sides["unjudged"].get("jev_agree_panel"):
        a = [x["jev"] == x["qrels"] for x in sides["judged"]["_recs"]]
        b = [x["jev"] == x["panel"] for x in sides["unjudged"]["_recs"] if x["panel"] is not None]
        rng = random.Random(SEED)
        bs = sorted(statistics.mean(rng.choice(a) for _ in a) - statistics.mean(rng.choice(b) for _ in b) for _ in range(2000))
        out["acc_judged_minus_unjudged"] = {"diff": statistics.mean(a) - statistics.mean(b), "ci": [bs[50], bs[1949]]}
        a2 = [x["jev"] == x["panel"] for x in sides["judged"]["_recs"] if x["panel"] is not None]
        if a2:
            bs2 = sorted(statistics.mean(rng.choice(a2) for _ in a2) - statistics.mean(rng.choice(b) for _ in b) for _ in range(2000))
            out["agree_panel_judged_minus_unjudged"] = {"diff": statistics.mean(a2) - statistics.mean(b), "ci": [bs2[50], bs2[1949]]}
    for s in sides.values():
        s.pop("_recs", None)
    out["sides"] = sides
    return out


# ------------------------------------------------------------------------------------------------ T4 Jeb Bush (offline, from the study's TREC run)

TREC_PANEL = ["gpt-5.6-luna", "gpt-5.6-terra", "claude-sonnet-5", "gemini-3.8-flash", "claude-haiku-4.5", "gemini-3.5-flash-lite"]


def score_t4_jebbush() -> dict:
    tmap = json.loads((DATA / "trec_topic_map.json").read_text())
    key2num = {v: k for k, v in tmap.items()}
    qrels: dict[tuple[str, str], int] = {}
    for line in (ROOT / "data" / "trec" / "raw" / "athome4.facetsandqrels").read_text().splitlines():
        p = line.split()
        if len(p) >= 3:
            qrels[(p[0], p[1].lstrip("0"))] = int(p[2])
    ids = {r["id"]: r for r in read_jsonl(ROOT / "data" / "trec" / "eval_ids.jsonl")}
    jev = {(r["doc_id"], r["question"]): r for r in read_jsonl(ROOT / "results" / "trec" / "multi" / "jev__base.jsonl") if not r.get("error")}
    panels = {m: {(r["doc_id"], r["question"]): r["label"] for r in read_jsonl(ROOT / "results" / "trec" / "multi" / f"{m}.jsonl") if not r.get("error")} for m in TREC_PANEL}
    panels = {m: v for m, v in panels.items() if v}
    if not jev or not panels:
        return {"note": "results/trec predictions not available"}
    recs = []
    for (doc, q), r in jev.items():
        if q == "eminent_domain" or q not in key2num or doc not in ids:
            continue
        docno = ids[doc]["meta"]["docno"]
        rel = qrels.get((key2num[q], docno))
        votes = [panels[m][(doc, q)] for m in panels if (doc, q) in panels[m]]
        c = Counter(votes)
        maj, n_maj = (c.most_common(1)[0] if votes else (None, 0))
        panel = maj if votes and n_maj >= max(4, len(votes) - 1) else None  # at most one dissenter
        recs.append({"doc": doc, "q": q, "judged": rel is not None, "gold": (POS if rel and rel > 0 else "not_responsive") if rel is not None else None,
                     "jev": r["label"], "panel": panel, "n_chars": ids[doc]["meta"].get("n_chars") or 0, "stratum": ids[doc]["meta"].get("stratum")})
    judged = [x for x in recs if x["judged"]]
    unj = [x for x in recs if not x["judged"]]
    # length-matched unjudged twin per judged pair, same topic
    rng = random.Random(SEED)
    pool = defaultdict(list)
    for x in unj:
        if x["panel"] is not None:
            pool[x["q"]].append(x)
    for v in pool.values():
        rng.shuffle(v)
    used = set()
    matched = []
    for j in judged:
        cands = [x for x in pool[j["q"]] if (x["doc"], x["q"]) not in used]
        if not cands:
            continue
        best = min(cands, key=lambda x: abs(x["n_chars"] - j["n_chars"]))
        used.add((best["doc"], best["q"]))
        matched.append(best)
    out = {"n_pairs_scored": len(recs), "n_judged": len(judged), "n_unjudged": len(unj), "n_unjudged_with_panel": sum(1 for x in unj if x["panel"] is not None),
           "n_matched": len(matched), "panel_models": list(panels), "panel_rule": "majority with at most one dissenter among the LLMs that answered",
           "judged": {"jev_acc_vs_qrels": _rate_block([x["jev"] == x["gold"] for x in judged]),
                      "jev_acc_by_gold": {g: _rate_block([x["jev"] == x["gold"] for x in judged if x["gold"] == g]) for g in (POS, "not_responsive")},
                      "qrels_positive_rate": _rate_block([x["gold"] == POS for x in judged]),
                      "jev_agree_panel": _rate_block([x["jev"] == x["panel"] for x in judged if x["panel"] is not None]),
                      "jev_agree_panel_by_panel": {g: _rate_block([x["jev"] == x["panel"] for x in judged if x["panel"] == g]) for g in (POS, "not_responsive")},
                      "panel_acc_vs_qrels": _rate_block([x["panel"] == x["gold"] for x in judged if x["panel"] is not None]),
                      "panel_positive_rate": _rate_block([x["panel"] == POS for x in judged if x["panel"] is not None]),
                      "n_chars_median": statistics.median(x["n_chars"] for x in judged) if judged else None},
           "unjudged_matched": {"jev_agree_panel": _rate_block([x["jev"] == x["panel"] for x in matched]),
                                "jev_agree_panel_by_panel": {g: _rate_block([x["jev"] == x["panel"] for x in matched if x["panel"] == g]) for g in (POS, "not_responsive")},
                                "panel_positive_rate": _rate_block([x["panel"] == POS for x in matched]),
                                "n_chars_median": statistics.median(x["n_chars"] for x in matched) if matched else None},
           "unjudged_all": {"jev_agree_panel": _rate_block([x["jev"] == x["panel"] for x in unj if x["panel"] is not None]),
                            "panel_positive_rate": _rate_block([x["panel"] == POS for x in unj if x["panel"] is not None])}}
    a = [x["jev"] == x["gold"] for x in judged]
    b = [x["jev"] == x["panel"] for x in matched]
    a2 = [x["jev"] == x["panel"] for x in judged if x["panel"] is not None]
    if a and b:
        bs = sorted(statistics.mean(rng.choice(a) for _ in a) - statistics.mean(rng.choice(b) for _ in b) for _ in range(2000))
        out["acc_judged_minus_unjudged"] = {"diff": statistics.mean(a) - statistics.mean(b), "ci": [bs[50], bs[1949]]}
    if a2 and b:
        bs = sorted(statistics.mean(rng.choice(a2) for _ in a2) - statistics.mean(rng.choice(b) for _ in b) for _ in range(2000))
        out["agree_panel_judged_minus_unjudged"] = {"diff": statistics.mean(a2) - statistics.mean(b), "ci": [bs[50], bs[1949]]}
    # by reference label, same-reference comparison
    for g in (POS, "not_responsive"):
        aa = [x["jev"] == x["panel"] for x in judged if x["panel"] == g]
        bb = [x["jev"] == x["panel"] for x in matched if x["panel"] == g]
        if aa and bb:
            bs = sorted(statistics.mean(rng.choice(aa) for _ in aa) - statistics.mean(rng.choice(bb) for _ in bb) for _ in range(2000))
            out[f"agree_panel_judged_minus_unjudged__panel_{g}"] = {"diff": statistics.mean(aa) - statistics.mean(bb), "ci": [bs[50], bs[1949]], "n": [len(aa), len(bb)]}
    return out


# ------------------------------------------------------------------------------------------------ all

T1_VERSION_NOTE = ("v2 (token-free contexts, 2026-10-04). v1 used the task-yaml contexts as sent to the study's systems; the Mallinckrodt and "
                   "Endo contexts named the opioid brands and the non-opioid decoys, so a real token in the document could match the prompt rather "
                   "than training knowledge. v2 replaces those two contexts with product-nameless versions (check C's) and asserts in code that no "
                   "T1 token appears in any context or request. Enron and Jeb Bush prompts were already token-free and their v1 predictions are "
                   "carried over unchanged; Mallinckrodt and Endo were re-run on all four systems. v1 is kept under t1_v1_confounded.")


def score_all(log=print) -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary = {
        "framing": "Jev is a system under test. Its vendor states it is trained on synthetic data; every result below is reported as evidence consistent or inconsistent with that statement, never as proof.",
        "t1": score_t1(), "t1_version": T1_VERSION_NOTE, "t1_v1_confounded": score_t1("t1_v1_confounded"),
        "bare_token": score_bare(), "t2": score_t2(), "t3": score_t3(),
        "t4": {"enron": score_t4_enron(), "jebbush": score_t4_jebbush()},
        "spend": {"openai_t1_t2_predictions": round(prediction_spend(["t1", "t1_v1_confounded", "t2"], exclude=T1_CARRIED_OVER), 4),
                  "openai_t1_v1_confounded": round(prediction_spend(["t1_v1_confounded"]), 4),
                  "openai_t1_v2_rerun": round(prediction_spend(["t1"], exclude=T1_CARRIED_OVER), 4),
                  "openai_t2_edits": round(ledger_total(["t2_edit"]), 4),
                  "openai_t3_paraphrases": round(ledger_total(["t3_para"]), 4), "openai_t3_t4_predictions": round(prediction_spend(["t3", "t4"]), 4),
                  "jev": round(prediction_spend(None, ["jev"], exclude=T1_CARRIED_OVER), 4)},
    }
    s = summary["spend"]
    s["openai_t1_t2_total"] = round(s["openai_t1_t2_predictions"] + s["openai_t2_edits"], 4)
    s["openai_total"] = round(s["openai_t1_t2_total"] + s["openai_t3_paraphrases"] + s["openai_t3_t4_predictions"], 4)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"wrote {RESULTS / 'summary.json'}; OpenAI spend ${s['openai_total']:.2f} (T1+T2 ${s['openai_t1_t2_total']:.2f}), Jev ${s['jev']:.3f}")
    return summary

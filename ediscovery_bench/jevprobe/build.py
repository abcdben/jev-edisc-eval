"""Deterministic data for every test -> data/jev_probe/. No API calls here (the Luna edits/paraphrases are in edit.py).

  t1_<matter>.jsonl        T1 documents, both conditions (meta.condition real|fake, meta.pair, meta.kind signal|decoy, meta.qid)
  t1_requests.json         the nameless requests and contexts as sent
  bt_docs.jsonl            bare-token documents (header + one sentence), real|fake, token in meta
  t2_<coll>.jsonl          T2 originals: enron (legal10 learning qrels), jebbush (athome4 qrels, local_subset text), veridian (our labels)
  t3_<corpus>.jsonl        T3 originals: enron, endo, veridian
  t4_enron_judged.jsonl    T4 judged Enron sample (learning-task qrels, 6 substantive topics)
  t4_enron_unjudged.jsonl  T4 unjudged Enron sample from the EDRM pool (pool.py), length-matched to the judged sample
  trec_topic_map.json      athome4 topic number -> task key
"""
from __future__ import annotations

import json
import random
import re
from collections import defaultdict

from .common import DATA, ROOT, SEED, read_jsonl, write_jsonl
from .items import BARE_SENTENCES, BARE_TOKENS, ENRON, MATTERS, header, swap
from .pool import POOL

ENRON_TOPICS = ["prepay_transactions", "fas140", "financial_forecasts", "document_destruction", "energy_schedules", "financial_analysts"]
TREC_TOPIC_MAP = {"403": "bottled_water", "404": "eminent_domain", "407": "faith_based", "410": "condominiums", "412": "recount_2000",
                  "414": "medicaid_reform", "415": "gw_bush", "416": "marketing", "417": "movie_gallery", "419": "rilya_wilson",
                  "422": "nra_aliens", "423": "nra_rifle"}
TREC_TASK_TOPICS = [k for k in TREC_TOPIC_MAP.values() if k != "eminent_domain"]
VERIDIAN_REQUESTS = ["rfp01_recall", "rfp02_design_history", "rfp03_complaints", "rfp04_fda", "rfp06_marketing", "rfp07_surgeon_payments",
                     "rfp08_sales_scripts", "rfp09_registry_decision", "rfp13_financials", "rfp17_personnel"]
_META_RE = re.compile(r"^X-(?:SDOC|ZLID|FileName|Folder|Origin):.*\n?", re.M)

# lexical cues used only to enrich the unjudged Enron pool for positives (the judged pool was retrieval-selected too)
ENRON_CUES = {
    "prepay_transactions": ["prepay", "prepaid", "mahonia", "yosemite"],
    "fas140": ["fas 140", "fas140", "fas 125", "securitiz", "raptor", "ljm", "chewco", "whitewing", "osprey", "special purpose", "spe "],
    "financial_forecasts": ["forecast", "earnings", "guidance", "eps", "projection", "plan target", "budget"],
    "document_destruction": ["shred", "retention", "destroy", "destruction", "delete", "deleted"],
    "energy_schedules": ["schedul", "load", " bid", "iso ", "megawatt", " mw", "caiso"],
    "financial_analysts": ["analyst", "merrill", "goldman", "salomon", "lehman", "csfb", "morgan", "coverage", "rating"],
}


def _clean_enron(text: str) -> str:
    return _META_RE.sub("", text)


# ------------------------------------------------------------------------------------------------ T1

def build_t1(log=print) -> dict:
    out_req = {}
    for key, m in MATTERS.items():
        rows = []
        for i, s in enumerate(m.scenarios):
            pair = f"t1_{key}_{i:02d}"
            real_subj, real_body = s.subject.replace("{T}", s.token), s.body.replace("{T}", s.token)
            real = header(m, i, real_subj) + real_body + "\n"
            fake = swap(real, m.tokens)
            assert fake != real, (key, i, s.token)
            for cond, text in (("real", real), ("fake", fake)):
                rows.append({"id": f"{pair}__{cond}", "text": text, "labels": {}, "gray": [],
                             "meta": {"pair": pair, "condition": cond, "token": s.token, "fake_token": m.tokens[s.token], "kind": s.kind,
                                      "qid": s.qid, "matter": key, "__unlabeled__": True}})
        write_jsonl(DATA / f"t1_{key}.jsonl", rows)
        ts = m.taskset(ROOT)
        out_req[key] = {"context": ts.context, "requests": {q: {"rfp_text": ts.questions[q].rfp_text, "positive_desc": ts.questions[q].positive_desc,
                                                                 "negative_desc": ts.questions[q].negative_desc} for q in ts.qids},
                        "tokens": m.tokens, "n_pairs": len(m.scenarios), "n_signal": sum(1 for s in m.scenarios if s.kind == "signal"),
                        "n_decoy": sum(1 for s in m.scenarios if s.kind == "decoy")}
        log(f"T1 {key}: {len(m.scenarios)} pairs ({out_req[key]['n_signal']} signal, {out_req[key]['n_decoy']} decoy), {len(ts.qids)} requests")
    (DATA / "t1_requests.json").write_text(json.dumps(out_req, indent=1, ensure_ascii=False))
    return out_req


# ------------------------------------------------------------------------------------------------ bare-token

def build_bare(log=print) -> int:
    rows = []
    for i, sent in enumerate(BARE_SENTENCES):
        for tok, fake in BARE_TOKENS.items():
            pair = f"bt_{i:02d}_{tok}"
            real = header(ENRON, i, f"{tok}") + sent.replace("{T}", tok) + "\n"
            fk = header(ENRON, i, f"{fake}") + sent.replace("{T}", fake) + "\n"
            rows.append({"id": f"{pair}__real", "text": real, "labels": {}, "gray": [], "meta": {"pair": pair, "condition": "real", "token": tok, "sentence": i, "__unlabeled__": True}})
            rows.append({"id": f"{pair}__fake", "text": fk, "labels": {}, "gray": [], "meta": {"pair": pair, "condition": "fake", "token": tok, "sentence": i, "__unlabeled__": True}})
    n = write_jsonl(DATA / "bt_docs.jsonl", rows)
    log(f"bare-token: {n} documents ({len(BARE_SENTENCES)} sentences x {len(BARE_TOKENS)} tokens x 2)")
    return n


# ------------------------------------------------------------------------------------------------ T2 originals

def _enron_rows(min_chars=400, max_chars=5000):
    for r in read_jsonl(ROOT / "data" / "legal10" / "learn.jsonl"):
        t = r.get("text") or ""
        if r["meta"].get("is_attachment") or not (min_chars <= len(t) <= max_chars):
            continue
        r["text"] = _clean_enron(t)
        yield r


def build_t2(n_per_coll: int = 100, log=print) -> dict:
    rng = random.Random(SEED)
    stats = {}
    # --- Enron: learning-task qrels, one judged topic per document
    by = defaultdict(list)
    for r in _enron_rows():
        for q, lab in r["labels"].items():
            if q in ENRON_TOPICS:
                by[(q, lab)].append(r)
    per = n_per_coll // (2 * len(ENRON_TOPICS))
    rows = []
    for q in ENRON_TOPICS:
        for lab in ("responsive", "not_responsive"):
            pool = by[(q, lab)]
            rng.shuffle(pool)
            for r in pool[:per]:
                rows.append({"id": r["id"], "text": r["text"], "labels": {q: lab}, "gray": [],
                             "meta": {"collection": "enron", "target_qid": q, "old_label": lab, "docid": r["meta"]["docid"], "n_chars": len(r["text"])}})
    # top up to n_per_coll alternating labels
    i = 0
    while len(rows) < n_per_coll:
        q = ENRON_TOPICS[i % len(ENRON_TOPICS)]; lab = ("responsive", "not_responsive")[(i // len(ENRON_TOPICS)) % 2]
        pool = by[(q, lab)]
        used = {r["id"] for r in rows}
        extra = [r for r in pool if r["id"] not in used]
        if extra:
            r = extra[0]
            rows.append({"id": r["id"], "text": r["text"], "labels": {q: lab}, "gray": [],
                         "meta": {"collection": "enron", "target_qid": q, "old_label": lab, "docid": r["meta"]["docid"], "n_chars": len(r["text"])}})
        i += 1
        if i > 100:
            break
    write_jsonl(DATA / "t2_enron.jsonl", rows)
    stats["enron"] = {"n": len(rows), "pos": sum(1 for r in rows if r["meta"]["old_label"] == "responsive")}
    # --- Jeb Bush: athome4 qrels on the 600 e-mails with text
    qrels = defaultdict(dict)
    for line in (ROOT / "data" / "trec" / "raw" / "athome4.facetsandqrels").read_text().splitlines():
        p = line.split()
        if len(p) >= 3:
            qrels[p[1].lstrip("0")][p[0]] = int(p[2])
    jb = read_jsonl(ROOT / "data" / "trec" / "local_subset.jsonl")
    pos_by, neg_by = defaultdict(list), defaultdict(list)
    for r in jb:
        js = qrels.get(r["meta"]["docno"], {})
        for t, v in js.items():
            k = TREC_TOPIC_MAP.get(t)
            if k is None or k == "eminent_domain" or not (300 <= len(r["text"]) <= 5000):
                continue
            (pos_by if v > 0 else neg_by)[k].append(r)
    rows = []
    want_pos, want_neg = n_per_coll // 2, n_per_coll - n_per_coll // 2
    for lab, src, want in (("responsive", pos_by, want_pos), ("not_responsive", neg_by, want_neg)):
        keys = sorted(src, key=lambda k: -len(src[k]))
        used = {r["id"] for r in rows}
        round_i = 0
        while sum(1 for r in rows if r["meta"]["old_label"] == lab) < want and round_i < 50:
            for k in keys:
                cands = [r for r in src[k] if r["id"] not in used]
                if cands:
                    r = cands[rng.randrange(len(cands))]
                    rows.append({"id": r["id"], "text": r["text"], "labels": {k: lab}, "gray": [],
                                 "meta": {"collection": "jebbush", "target_qid": k, "old_label": lab, "docno": r["meta"]["docno"], "n_chars": len(r["text"])}})
                    used.add(r["id"])
                    if sum(1 for x in rows if x["meta"]["old_label"] == lab) >= want:
                        break
            round_i += 1
    write_jsonl(DATA / "t2_jebbush.jsonl", rows)
    stats["jebbush"] = {"n": len(rows), "pos": sum(1 for r in rows if r["meta"]["old_label"] == "responsive")}
    # --- Veridian: our own labels (no public label exists); the calibration arm
    vr = [r for r in read_jsonl(ROOT / "data" / "veridian" / "veridian.jsonl") if 300 <= len(r["text"]) <= 5000]
    rng.shuffle(vr)
    rows = []
    per = n_per_coll // (2 * len(VERIDIAN_REQUESTS))
    for q in VERIDIAN_REQUESTS:
        pos = [r for r in vr if r["labels"].get(q) == "responsive" and q not in (r.get("gray") or [])][:per]
        neg = [r for r in vr if q not in r["labels"] and q not in (r.get("gray") or [])][:per]
        for lab, lst in (("responsive", pos), ("not_responsive", neg)):
            for r in lst:
                rows.append({"id": r["id"], "text": r["text"], "labels": {q: lab}, "gray": [],
                             "meta": {"collection": "veridian", "target_qid": q, "old_label": lab, "n_chars": len(r["text"])}})
    write_jsonl(DATA / "t2_veridian.jsonl", rows)
    stats["veridian"] = {"n": len(rows), "pos": sum(1 for r in rows if r["meta"]["old_label"] == "responsive")}
    log(f"T2 originals: {stats}")
    return stats


# ------------------------------------------------------------------------------------------------ T3 originals

def build_t3(n: int = 100, min_chars: int = 400, max_chars: int = 3500, log=print) -> dict:
    rng = random.Random(SEED + 1)
    stats = {}
    en = [r for r in _enron_rows(min_chars, max_chars) if any(q in ENRON_TOPICS for q in r["labels"])]
    rng.shuffle(en)
    rows = [{"id": r["id"], "text": r["text"], "labels": {q: l for q, l in r["labels"].items() if q in ENRON_TOPICS}, "gray": [],
             "meta": {"corpus": "enron", "n_chars": len(r["text"])}} for r in en[:n]]
    write_jsonl(DATA / "t3_enron.jsonl", rows); stats["enron"] = len(rows)
    endo = [r for r in read_jsonl(ROOT / "data" / "endo" / "endo.jsonl") if min_chars <= len(r["text"]) <= max_chars]
    rng.shuffle(endo)
    rows = [{"id": r["id"], "text": r["text"], "labels": r["labels"], "gray": r.get("gray") or [], "meta": {"corpus": "endo", "n_chars": len(r["text"])}} for r in endo[:n]]
    write_jsonl(DATA / "t3_endo.jsonl", rows); stats["endo"] = len(rows)
    ver = [r for r in read_jsonl(ROOT / "data" / "veridian" / "veridian.jsonl") if min_chars <= len(r["text"]) <= max_chars]
    rng.shuffle(ver)
    rows = [{"id": r["id"], "text": r["text"], "labels": r["labels"], "gray": r.get("gray") or [], "meta": {"corpus": "veridian", "n_chars": len(r["text"])}} for r in ver[:n]]
    write_jsonl(DATA / "t3_veridian.jsonl", rows); stats["veridian"] = len(rows)
    log(f"T3 originals: {stats}")
    return stats


# ------------------------------------------------------------------------------------------------ T4 Enron

def build_t4(n_judged: int = 150, log=print) -> dict:
    rng = random.Random(SEED + 2)
    by = defaultdict(list)
    for r in _enron_rows(400, 6000):
        for q, lab in r["labels"].items():
            if q in ENRON_TOPICS:
                by[(q, lab)].append(r)
    per = max(1, n_judged // (2 * len(ENRON_TOPICS)))
    judged = []
    for q in ENRON_TOPICS:
        for lab in ("responsive", "not_responsive"):
            pool = by[(q, lab)]
            rng.shuffle(pool)
            for r in pool[:per]:
                judged.append({"id": r["id"], "text": r["text"], "labels": {q: lab}, "gray": [],
                               "meta": {"collection": "enron", "judged": True, "topic_key": q, "qrels_label": lab, "docid": r["meta"]["docid"], "n_chars": len(r["text"])}})
    write_jsonl(DATA / "t4_enron_judged.jsonl", judged)
    stats = {"judged": len(judged), "judged_pos": sum(1 for r in judged if r["meta"]["qrels_label"] == "responsive")}
    if not POOL.exists():
        log("T4: EDRM pool not built yet (run the scan); unjudged sample skipped")
        return stats
    pool = read_jsonl(POOL)
    # enrich: a doc is a candidate for topic q if it hits a cue of q; else random
    cands = defaultdict(list)
    for r in pool:
        low = r["text"].lower()
        hits = [q for q, cues in ENRON_CUES.items() if any(c in low for c in cues)]
        for q in hits:
            cands[q].append(r)
        if not hits:
            cands["_random"].append(r)
    for v in cands.values():
        rng.shuffle(v)
    used: set[str] = set()
    unjudged = []
    # one length-matched twin per judged document: same topic for cue-enriched twins (half), random for the other half
    for i, j in enumerate(judged):
        q = j["meta"]["topic_key"]
        src = cands[q] if (i % 2 == 0 and cands[q]) else cands["_random"]
        avail = [r for r in src if r["id"] not in used] or [r for r in pool if r["id"] not in used]
        if not avail:
            break
        best = min(avail, key=lambda r: abs(len(r["text"]) - len(j["text"])))
        used.add(best["id"])
        unjudged.append({"id": best["id"], "text": best["text"], "labels": {}, "gray": [],
                         "meta": {"collection": "enron", "judged": False, "topic_key": q, "matched_to": j["id"], "enriched": src is cands[q],
                                  "docid": best["meta"]["docid"], "n_chars": len(best["text"]), "__unlabeled__": True}})
    write_jsonl(DATA / "t4_enron_unjudged.jsonl", unjudged)
    stats.update({"unjudged": len(unjudged), "pool": len(pool), "enriched": sum(1 for r in unjudged if r["meta"]["enriched"])})
    log(f"T4 Enron: {stats}")
    return stats


def build(log=print, skip_t4: bool = False) -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "trec_topic_map.json").write_text(json.dumps(TREC_TOPIC_MAP, indent=1))
    out = {"t1": build_t1(log), "bare": build_bare(log), "t2": build_t2(log=log), "t3": build_t3(log=log)}
    if not skip_t4:
        out["t4"] = build_t4(log=log)
    return out

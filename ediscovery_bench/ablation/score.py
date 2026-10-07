"""Score the pseudonymisation ablation → results/ablation/summary.json + REPORT.md.

For every arm × model the two conditions are compared on exactly the same (document, request) pairs:
  metrics          precision / recall / F1 / accuracy per condition, per topic and pooled
  delta            renamed − named for each metric, with a cluster (by document) bootstrap 95% CI and an exact
                   McNemar p-value on the discordant pairs
  flips            correct→wrong / wrong→correct counts, split by gold label (lost positives = recall damage,
                   new false positives = precision damage)
  dose             Enron arms: Δ by number of knowledge-bearing names in the document (0, 1–2, 3+)
  contrasts        knowledge effect = Δ(Enron J) − Δ(Enron K) for every system, with Δ(Veridian) alongside; bootstrap CIs
  leak             residual-leakage check: share of renamed documents the model still attributes to Enron (LLMs only —
                   the question is generative and cannot be posed to a classifier)
Jev is a fourth system under test and is scored identically. Its vendor states it is not pre-trained on these corpora;
we treat that as a claim and test it: a J − K effect near zero is consistent with the claim, a positive effect comparable
to the LLMs' is not. When no Jev rows exist the Jev entries are marked pending.
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from ..runner import load_predictions, parse_job_stem
from .build import ARMS, DATA
from .run import ALL_MODELS, JEV, LLM_MODELS, RESULTS, score_leak

B = 2000
RNG = np.random.default_rng(2026)
ARM_LABEL = {"enron_j": "Enron — Complaint J (knowledge-rich)", "enron_k": "Enron — Complaint K (knowledge-poor control)",
             "veridian": "Veridian (fictional; renaming cost only)", "mnk": "Mallinckrodt (± case brief)"}
COND_LABEL = {"enron_j": ("named", "renamed"), "enron_k": ("named", "renamed"), "veridian": ("named", "renamed"), "mnk": ("no brief", "with brief")}
CONTROL_TOPIC = "fantasy_football"


# ------------------------------------------------------------------------------------------------ loading

def load_rows() -> dict[tuple[str, str, str], dict[tuple[str, str], dict]]:
    """(arm, model, condition) → {(doc_id, question): {"pred": 0/1, "gold": 0/1, "topic": str, "cost":…, "list":…}}"""
    out: dict = defaultdict(dict)
    for f in RESULTS.glob("*/multi/*.jsonl"):
        arm = f.parts[-3]
        model, tag = parse_job_stem(f.stem)
        cond, _, topic = tag.partition("__")
        for p in load_predictions(f):
            if p.error or p.gold is None or not p.label:
                continue
            out[(arm, model, cond)][(p.doc_id, p.question)] = {
                "pred": 1 if p.label == "responsive" else 0, "gold": 1 if p.gold == "responsive" else 0,
                "topic": p.question if ARMS[arm]["per_doc_topic"] else "all", "cost": p.cost_usd, "list": p.list_cost_usd,
                "p": p.p_positive,
            }
    return out


def load_doses() -> dict[str, dict[str, int]]:
    out = {}
    for arm in ("enron_j", "enron_k", "veridian"):
        p = DATA / f"{arm}__renamed.jsonl"
        if p.exists():
            out[arm] = {json.loads(l)["id"]: json.loads(l)["meta"].get("dose", 0) for l in p.read_text().splitlines() if l.strip()}
    return out


# ------------------------------------------------------------------------------------------------ metrics

def prf(gold: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(((gold == 1) & (pred == 1)).sum())
    fp = int(((gold == 0) & (pred == 1)).sum())
    fn = int(((gold == 1) & (pred == 0)).sum())
    tn = int(((gold == 0) & (pred == 0)).sum())
    P = tp / (tp + fp) if tp + fp else float("nan")
    R = tp / (tp + fn) if tp + fn else float("nan")
    F = 2 * P * R / (P + R) if (tp + fp and tp + fn and P + R) else (0.0 if tp + fn else float("nan"))
    return {"n": int(len(gold)), "pos": tp + fn, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": P, "recall": R, "f1": F,
            "accuracy": (tp + tn) / len(gold) if len(gold) else float("nan")}


def _prf_vec(gold, pred):
    """precision, recall, f1, accuracy as floats (nan-safe) for bootstrap."""
    tp = ((gold == 1) & (pred == 1)).sum(); fp = ((gold == 0) & (pred == 1)).sum(); fn = ((gold == 1) & (pred == 0)).sum()
    P = tp / (tp + fp) if tp + fp else np.nan
    R = tp / (tp + fn) if tp + fn else np.nan
    F = 2 * P * R / (P + R) if (tp + fp and tp + fn and (P + R) > 0) else (0.0 if tp + fn else np.nan)
    return P, R, F, (gold == pred).mean()


def _clusters(keys: list[tuple[str, str]]) -> list[np.ndarray]:
    by = defaultdict(list)
    for i, (d, _) in enumerate(keys):
        by[d].append(i)
    return [np.array(v) for v in by.values()]


def boot_delta(gold, a, b, clusters, nb=B) -> dict:
    """Bootstrap (by document) of metric(b) − metric(a). Returns per-metric point estimate and 95% CI."""
    names = ("precision", "recall", "f1", "accuracy")
    point = np.array(_prf_vec(gold, b)) - np.array(_prf_vec(gold, a))
    nC = len(clusters)
    samples = np.empty((nb, 4))
    for i in range(nb):
        pick = RNG.integers(0, nC, nC)
        idx = np.concatenate([clusters[j] for j in pick])
        samples[i] = np.array(_prf_vec(gold[idx], b[idx])) - np.array(_prf_vec(gold[idx], a[idx]))
    out = {}
    for k, nm in enumerate(names):
        col = samples[:, k]
        col = col[~np.isnan(col)]
        out[nm] = {"delta": float(point[k]) if not np.isnan(point[k]) else None,
                   "lo": float(np.percentile(col, 2.5)) if len(col) else None, "hi": float(np.percentile(col, 97.5)) if len(col) else None}
    return out, samples


def mcnemar(a_correct: np.ndarray, b_correct: np.ndarray) -> dict:
    b_ = int((a_correct & ~b_correct).sum())  # right under A, wrong under B
    c_ = int((~a_correct & b_correct).sum())
    n = b_ + c_
    if n == 0:
        return {"lost": b_, "gained": c_, "p": 1.0}
    k = min(b_, c_)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n)
    return {"lost": b_, "gained": c_, "p": p}


def flips(gold, a, b) -> dict:
    ac, bc = a == gold, b == gold
    return {
        "both_right": int((ac & bc).sum()), "both_wrong": int((~ac & ~bc).sum()),
        "right_to_wrong": int((ac & ~bc).sum()), "wrong_to_right": int((~ac & bc).sum()),
        "positives_lost": int(((gold == 1) & (a == 1) & (b == 0)).sum()), "positives_gained": int(((gold == 1) & (a == 0) & (b == 1)).sum()),
        "false_pos_added": int(((gold == 0) & (a == 0) & (b == 1)).sum()), "false_pos_removed": int(((gold == 0) & (a == 1) & (b == 0)).sum()),
    }


# ------------------------------------------------------------------------------------------------ per arm × model

def pair(rows, arm, model, doses) -> dict | None:
    ca, cb = "named", "renamed"
    A, Bm = rows.get((arm, model, ca), {}), rows.get((arm, model, cb), {})
    keys = sorted(set(A) & set(Bm))
    if not keys:
        return None
    gold = np.array([A[k]["gold"] for k in keys]); a = np.array([A[k]["pred"] for k in keys]); b = np.array([Bm[k]["pred"] for k in keys])
    topics = np.array([A[k]["topic"] for k in keys])
    dose = np.array([doses.get(arm, {}).get(k[0], 0) for k in keys])
    clusters = _clusters(keys)
    res = {"n_pairs": len(keys), "n_docs": len(clusters), "topics": {}, "cost_usd": {ca: sum(A[k]["cost"] for k in keys), cb: sum(Bm[k]["cost"] for k in keys)},
           "list_usd": {ca: sum(A[k]["list"] for k in keys), cb: sum(Bm[k]["list"] for k in keys)}}
    # main (knowledge topics only for Enron J: fantasy football is reported separately as the in-mailbox control)
    main = topics != CONTROL_TOPIC if arm == "enron_j" else np.ones(len(keys), bool)
    mi = np.where(main)[0]
    sub_clusters = _clusters([keys[i] for i in mi])
    res["named"] = prf(gold[mi], a[mi]); res["renamed"] = prf(gold[mi], b[mi])
    res["delta"], samples = boot_delta(gold[mi], a[mi], b[mi], sub_clusters)
    res["_samples"] = samples
    res["mcnemar"] = mcnemar(a[mi] == gold[mi], b[mi] == gold[mi])
    res["flips"] = flips(gold[mi], a[mi], b[mi])
    for t in sorted(set(topics)):
        ti = np.where(topics == t)[0]
        d, _ = boot_delta(gold[ti], a[ti], b[ti], _clusters([keys[i] for i in ti]), nb=500)
        res["topics"][t] = {"named": prf(gold[ti], a[ti]), "renamed": prf(gold[ti], b[ti]), "delta": d, "flips": flips(gold[ti], a[ti], b[ti]),
                            "mcnemar": mcnemar(a[ti] == gold[ti], b[ti] == gold[ti])}
    if arm in ("enron_j", "enron_k", "veridian"):
        res["dose"] = {}
        for band, lo, hi in (("0", 0, 0), ("1-2", 1, 2), ("3+", 3, 10**9)):
            di = np.where(main & (dose >= lo) & (dose <= hi))[0]
            if len(di) < 10:
                continue
            d, _ = boot_delta(gold[di], a[di], b[di], _clusters([keys[i] for i in di]), nb=500)
            res["dose"][band] = {"n": int(len(di)), "named": prf(gold[di], a[di]), "renamed": prf(gold[di], b[di]), "delta": d, "flips": flips(gold[di], a[di], b[di])}
    # per-document agreement (did the label change at all?)
    res["label_changed_share"] = float((a != b).mean())
    return res


def contrast(sa: np.ndarray | None, sb: np.ndarray | None, pa: dict | None, pb: dict | None) -> dict | None:
    """Difference of two independent bootstrap delta distributions (a − b) per metric."""
    if sa is None or sb is None:
        return None
    names = ("precision", "recall", "f1", "accuracy")
    n = min(len(sa), len(sb))
    out = {}
    for k, nm in enumerate(names):
        d = sa[:n, k] - sb[:n, k]
        d = d[~np.isnan(d)]
        da, db = pa[nm]["delta"], pb[nm]["delta"]
        out[nm] = {"delta": (da - db) if da is not None and db is not None else None,
                   "lo": float(np.percentile(d, 2.5)) if len(d) else None, "hi": float(np.percentile(d, 97.5)) if len(d) else None}
    return out


# ------------------------------------------------------------------------------------------------ driver

def score_all(log=print) -> dict:
    rows = load_rows()
    doses = load_doses()
    models = [m for m in ALL_MODELS if any(k[1] == m for k in rows)]
    jev_present = JEV in models
    summary: dict = {"models": models, "llm_models": [m for m in LLM_MODELS if m in models], "jev": JEV, "jev_present": jev_present,
                     "jev_status": "present" if jev_present else "pending: TYPESAFE_API_KEY not set",
                     "jev_framing": "Jev's vendor states it is not pre-trained on these corpora; we treat that as a claim and test it.",
                     "arms": {}, "contrasts": {}, "cost": {}}
    S: dict[tuple[str, str], np.ndarray] = {}
    for arm in ARMS:
        summary["arms"][arm] = {"label": ARM_LABEL[arm], "conditions": COND_LABEL[arm], "per_model": {}}
        for m in ALL_MODELS:
            r = pair(rows, arm, m, doses)
            if r is None:
                summary["arms"][arm]["per_model"][m] = {"status": "pending" if m == JEV and not jev_present else "missing"}
                continue
            S[(arm, m)] = r.pop("_samples")
            r["status"] = "ok"
            summary["arms"][arm]["per_model"][m] = r
            log(f"{arm:9s} {m:14s} n={r['n_pairs']:5d}  F1 {r['named']['f1']:.3f}→{r['renamed']['f1']:.3f} (Δ {r['delta']['f1']['delta']:+.3f} "
                f"[{r['delta']['f1']['lo']:+.3f},{r['delta']['f1']['hi']:+.3f}])  R Δ {r['delta']['recall']['delta']:+.3f}  P Δ {r['delta']['precision']['delta']:+.3f}  "
                f"flips {r['flips']['right_to_wrong']}↓ {r['flips']['wrong_to_right']}↑  p={r['mcnemar']['p']:.3g}")
    # contrasts
    for m in ALL_MODELS:
        pm = {arm: summary["arms"][arm]["per_model"].get(m, {}) for arm in ARMS}
        c: dict = {}
        c["j_minus_k"] = contrast(S.get(("enron_j", m)), S.get(("enron_k", m)), pm["enron_j"].get("delta"), pm["enron_k"].get("delta"))
        c["j_minus_veridian"] = contrast(S.get(("enron_j", m)), S.get(("veridian", m)), pm["enron_j"].get("delta"), pm["veridian"].get("delta"))
        summary["contrasts"][m] = c
    # in-mailbox control topic
    summary["control_topic"] = {m: summary["arms"]["enron_j"]["per_model"].get(m, {}).get("topics", {}).get(CONTROL_TOPIC) for m in models}
    # leak check
    lp = RESULTS / "leak_check.jsonl"
    summary["leak"] = score_leak([json.loads(l) for l in lp.read_text().splitlines() if l.strip()]) if lp.exists() else {}
    lp1 = RESULTS / "leak_check_v1_with_metadata.jsonl"
    summary["leak_v1"] = score_leak([json.loads(l) for l in lp1.read_text().splitlines() if l.strip()]) if lp1.exists() else {}
    # cost
    for m in models:
        c = sum(v["cost"] for (a, mm, cond), d in rows.items() if mm == m for v in d.values())
        li = sum(v["list"] for (a, mm, cond), d in rows.items() if mm == m for v in d.values())
        n = sum(len(d) for (a, mm, cond), d in rows.items() if mm == m)
        summary["cost"][m] = {"paid_usd": round(c, 2), "list_usd": round(li, 2), "rows": n}
    summary["total_paid_usd"] = round(sum(v["paid_usd"] for v in summary["cost"].values()), 2)
    summary["total_list_usd"] = round(sum(v["list_usd"] for v in summary["cost"].values()), 2)
    # superseded runs kept beside the live files (results/ablation/<arm>/multi/leaky_v1/): counted for the ledger, not scored
    sup = 0.0
    for f in RESULTS.glob("*/multi/leaky_v1/*.jsonl"):
        sup += sum(p.cost_usd for p in load_predictions(f) if not p.error)
    summary["superseded_paid_usd"] = round(sup, 2)
    mapping = json.loads((DATA / "mapping.json").read_text()) if (DATA / "mapping.json").exists() else {}
    summary["mapping_stats"] = mapping.get("stats", {})
    summary["mapping_sizes"] = {"enron_phrases": len(mapping.get("enron", {}).get("phrases", {})), "enron_people": len(mapping.get("enron", {}).get("people", {})),
                                "veridian_phrases": len(mapping.get("veridian", {}).get("phrases", {})), "veridian_people": len(mapping.get("veridian", {}).get("people", {}))}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1, default=_json_default))
    md = report_md(summary)
    bt = RESULTS / "bigthorium" / "summary.json"
    if bt.exists():  # sixth collection (Big Thorium: the Relativity aiR for Review demo workspace, public documents, invented case), scored by ablation/bigthorium.py with its own panel gold
        b = json.loads(bt.read_text())
        cells = "; ".join(f"{m} {100 * r['delta']['f1']['delta']:+.1f} [{100 * r['delta']['f1']['lo']:+.1f}, {100 * r['delta']['f1']['hi']:+.1f}]" for m, r in b.get("rename", {}).items())
        md += (f"\n\n## Big Thorium (public documents, invented case; `results/ablation/bigthorium/REPORT.md`)\n\nThe Relativity aiR for Review demo workspace, distributed by Relativity, {b['n_docs']} documents, eight requests, panel gold "
               f"(leave-one-out). Named → renamed ΔF1: {cells}. Not part of the summary tables above (different gold procedure); see its own report and `design/07_ablation_round2.md` §C.\n")
    (RESULTS / "REPORT.md").write_text(md)
    log(f"wrote {RESULTS / 'summary.json'} and REPORT.md; total paid ${summary['total_paid_usd']:.2f} (list ${summary['total_list_usd']:.2f})")
    return summary


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        v = o.item()
        return None if isinstance(v, float) and math.isnan(v) else v
    if isinstance(o, float) and math.isnan(o):
        return None
    raise TypeError(str(type(o)))


# ------------------------------------------------------------------------------------------------ markdown

def _f(v, nd=3):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def _d(d: dict | None, k="f1"):
    if not d or d.get(k) is None or d[k].get("delta") is None:
        return "–"
    x = d[k]
    return f"{100*x['delta']:+.1f} pp [{100*x['lo']:+.1f}, {100*x['hi']:+.1f}]"


def report_md(s: dict) -> str:
    L = ["# Pseudonymisation ablation — results", "",
         f"Systems under test: {', '.join(s['models'])}. Jev: {s['jev_status']}. {s['jev_framing']}", "",
         f"Total spend: ${s['total_paid_usd']:.2f} paid (${s['total_list_usd']:.2f} list)"
         + (f"; a further ${s['superseded_paid_usd']:.2f} paid for the superseded Veridian renamed run (renamer v1, kept in `veridian/multi/leaky_v1/`, see the renamer audit below)." if s.get("superseded_paid_usd") else "."), "",
         "## Paired Δ (renamed − named), pooled over knowledge topics", "",
         "| arm | model | n pairs | F1 named | F1 renamed | ΔF1 [95% CI] | ΔRecall | ΔPrecision | right→wrong | wrong→right | McNemar p |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, A in s["arms"].items():
        for m in ALL_MODELS:
            r = A["per_model"].get(m, {})
            if r.get("status") != "ok":
                L.append(f"| {arm} | {m} | – | – | – | {r.get('status','missing')} | | | | | |")
                continue
            L.append(f"| {arm} | {m} | {r['n_pairs']} | {_f(r['named']['f1'])} | {_f(r['renamed']['f1'])} | {_d(r['delta'])} | {_d(r['delta'],'recall')} | {_d(r['delta'],'precision')} | "
                     f"{r['flips']['right_to_wrong']} | {r['flips']['wrong_to_right']} | {r['mcnemar']['p']:.3g} |")
    L += ["", "## Knowledge effect (all four systems; Jev's no-pre-training statement is a claim under test)", "",
          "| system | ΔF1(J) | ΔF1(K) | ΔF1(Veridian) | knowledge effect ΔF1(J) − ΔF1(K) | ΔF1(J) − ΔF1(Veridian) |", "|---|---|---|---|---|---|"]
    for m in s["models"]:
        c = s["contrasts"].get(m, {})
        pm = {arm: s["arms"][arm]["per_model"].get(m, {}) for arm in ("enron_j", "enron_k", "veridian")}
        L.append(f"| {m} | {_d(pm['enron_j'].get('delta'))} | {_d(pm['enron_k'].get('delta'))} | {_d(pm['veridian'].get('delta'))} | {_d(c.get('j_minus_k'))} | {_d(c.get('j_minus_veridian'))} |")
    L += ["", "## Dose–response (Enron J, ΔF1 by knowledge-bearing names per document)", "", "| model | 0 names | 1–2 | 3+ |", "|---|---|---|---|"]
    for m in s["models"]:
        r = s["arms"]["enron_j"]["per_model"].get(m, {})
        if r.get("status") == "ok":
            L.append(f"| {m} | " + " | ".join(f"{_d(r['dose'][b]['delta'])} (n={r['dose'][b]['n']})" if b in r.get("dose", {}) else "–" for b in ("0", "1-2", "3+")) + " |")
    L += ["", "## Residual leakage (renamed Enron J documents still attributed to Enron; LLMs only — the identification question is generative and cannot be posed to Jev)", ""]
    for m, v in s.get("leak", {}).items():
        L.append(f"- {m}: {v['named_enron']}/{v['n']} ({100*v['named_enron']/max(1,v['n']):.1f}%); by dose " +
                 ", ".join(f"{b}: {d['named_enron']}/{d['n']}" for b, d in v["by_dose"].items()) + f"; top guesses {v['top_guesses'][:4]}")
    L += ["", "## In-mailbox control topic (fantasy football, Enron J)", ""]
    for m, t in (s.get("control_topic") or {}).items():
        if t:
            L.append(f"- {m}: F1 {_f(t['named']['f1'])} → {_f(t['renamed']['f1'])}, Δ {_d(t['delta'])}")
    L += ["", RENAMER_AUDIT_MD]
    return "\n".join(L) + "\n"


RENAMER_AUDIT_MD = """## Renamer audit (2026-10-06)

Every renamed or paraphrased set was scanned for residual originals, over-replacement and request/document inconsistency, and the
per-request recall losses were tied back to the documents that carried residuals (`renamer_audit.md` in this folder has the full tables).

**Veridian renamed — defect found and fixed; re-run.** Renamer v1 mapped `ApexHip` and `Apex Registry` but not the bare short form, so 246
of 1,000 renamed documents still said "Apex reserve", "Apex booth", "Apex price" beside "SummitHip"; the surgeons named in the requests,
Feld and Rao, were in the common-word surname class and survived as "Dr. Feld", "Feld's" and bare "Rao" in 109 documents while the renamed
requests said Brandt and Menon; `General Counsel` became `General Wexham` (27) and `Quality Manager` became `Quality Harhurst` (5);
224 e-mail addresses in 144 documents kept the old local part (`mlee@`) beside the renamed display name. 120 of the 138 responsive documents
the four systems lost after renaming (on the six requests with a ≥ 5-point recall drop) were in leak-touched documents; on clean documents
ΔF1 was Luna +0.7, Terra −2.0, Sol −1.5, Jev +0.2 against −0.5 / −5.0 / −3.5 / −3.5 on touched ones. Renamer v2 (`names.py`, `build.py`;
`mapping.json` carries `version: 2`) maps bare Apex/Northgate/Meridian/Aegis, replaces Feld, Rao, Mitchell, Barr, Castellano, Tran, Vance,
Shah, Berg and Reid wherever they appear, excludes role words from the name tables, handles title and initial positions ("Dr. Feld",
"D. Mitchell") and three-letter surnames in e-mail local parts, and treats an underscore as a word boundary (attachment names). After the
fix the residual counts are 0 for Apex, Feld, Rao, Mitchell, Wexham, Harhurst and old local parts; the remaining residuals are ordinary
words that are also surnames (Central Park, Lee Hecht Harrison; about a dozen documents) and are left by design. The renamed condition was re-run on
all four systems with the v2 file (`data/ablation/veridian__renamed.jsonl`; v1 kept as `veridian__renamed.leaky_v1.jsonl`); the v1 run
outputs are in `veridian/multi/leaky_v1/`. The Veridian rows above, the ΔF1(J) − ΔF1(Veridian) column and the round-2 "CUAD − Veridian"
contrasts use the v2 run.

**Enron J / K renamed — cosmetic; not re-run.** No `Enron`/`ENE` residue in text or addresses. The header-derived surname table contains
ordinary words that were replaced wherever capitalised: `Scheduling`→Melwick (18 docs per arm), `Gov.`→`Lanford.` (19 / 24), `May`→Strounan
in date lines (12 / 10), `Risk Management`→`Risk Rosman`, `Businesses`→Dunman; 69 (J) / 68 (K) documents carry a mangle. 9 of 18 lost
energy_schedules positives are in mangled documents; no other request is touched. The knowledge effect recomputed on documents without a
mangle is Luna +1.2, Sol +1.8, Terra −1.0, Jev 0.0 against the published +1.6 / +2.1 / −2.6 / 0.0, every interval including zero either way.
A re-run (realised $9.4) would move Terra's point estimate about 1.6 points toward zero and change no conclusion, so the v1 files stand.

**Jeb Bush renamed — cosmetic; not re-run.** No `Jeb`/`Bush` in any body text; `jebbush@myflorida.com` and `georgewbush.com` in one
document each. Title-plus-public-surname forms survive in 22 documents (Senator Graham, Mayor Hood, Speaker Byrd, Congressman Foley),
more often in matter positives (13 of 273) than control positives (4 of 360); the knowledge effect on the 958 documents without any such
residual is Luna +0.9, Sol +0.6, Terra −2.5, Jev −2.9 against +1.1 / +0.1 / −2.4 / −3.2 on all documents. `Washington`→Drayman (49) and
`Vice President`→`Vice Tolwood` (19) are mangles balanced across matter and control topics. The recall drop on the gw_bush topic occurs on
clean documents and is the measured effect, not a defect.

**CUAD renamed — cosmetic.** Unmapped party acronyms and short names (SIGA, NFLA, KI, HPIL, MINDA/IMPCO, Columbia Laboratories) remain in
about 60 excerpts from 9 contracts; recall on those excerpts did not change for any system, so the residue affects identification only.

**CUAD paraphrased — caveat on one result.** The fidelity judge rated 11 of 100 sampled paraphrases not legally equivalent (change_of_control
2/5, license_grant 2/10, anti_assignment 2/11, ip_ownership_assignment 1/7, non_compete 1/6, insurance 1/2). Luna's and Jev's per-clause
recall drops of ≥ 5 points fall on the same clause types, so Luna's paraphrase ΔF1 of −1.3 [−2.7, −0.0] is consistent with roughly 10 %
infidelity rather than knowledge. The "CUAD − Veridian" paraphrase contrasts are unaffected in sign or significance. The Veridian paraphrase
control (49 of 50 equivalent; recall flat on every request) is clean.
"""

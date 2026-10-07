"""Score round 2 → results/ablation/round2/{summary.json, REPORT.md, fig_cuad.png, fig_jeb.png}.

Pairs (same documents, same requests, in both conditions):
  cuad      named → renamed; named → paraphrased          cluster bootstrap by contract (102 clusters); McNemar; flips
  veridian  named (round 1) → paraphrased                 the perturbation-cost control for the paraphrase arm
  veridian  named → renamed (round 1 files)               the renaming-cost floor, re-scored here so its bootstrap draws can be contrasted
  jeb       named → renamed                               all 12 requests; matter topics and control topics scored on the same documents
Knowledge effects (difference of bootstrap delta distributions, 95 % CI):
  CUAD rename      Δ(CUAD renamed) − Δ(Veridian renamed)
  CUAD paraphrase  Δ(CUAD paraphrased) − Δ(Veridian paraphrased)
  Jeb              Δ(matter topics) − Δ(control topics), paired within each bootstrap draw
Dose–response: CUAD by per-contract memorisation (finish-the-document LCS-F1 on the contract's original text, pooled over Luna/Terra/Sol,
terciles + Spearman of per-contract Δaccuracy vs dose); Jeb by mentions of public figures other than the Governor (0 / 1–2 / 3+).
Jev is a system under test and is scored identically.
"""
from __future__ import annotations

import html
import json
import math
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from ..runner import load_predictions, parse_job_stem
from .round2 import ARMS2, DATA, JEB_CONTROL, JEB_MATTER, RESULTS, ROOT, SPEND, cost_table, score_leak
from .run import ALL_MODELS, JEV, LLM_MODELS
from .run import RESULTS as R1_RESULTS
from .score import B, RNG, _clusters, _json_default, _prf_vec, boot_delta, contrast, flips, mcnemar, prf

MODELS_ORDER = [m for m in ALL_MODELS]
COND_LABEL = {"renamed": "renamed", "paraphrased": "paraphrased"}


# ------------------------------------------------------------------------------------------------ loading

def _load_file(f: Path, cluster_of, topic_of=None) -> dict:
    out = {}
    for p in load_predictions(f):
        if p.error or p.gold is None or not p.label:
            continue
        out[(p.doc_id, p.question)] = {"pred": 1 if p.label == "responsive" else 0, "gold": 1 if p.gold == "responsive" else 0,
                                       "cluster": cluster_of(p.doc_id), "topic": p.question, "cost": p.cost_usd, "list": p.list_cost_usd}
    return out


def load_rows() -> dict[tuple[str, str, str], dict]:
    """(arm, model, condition) → {(doc, q): row}. Veridian 'named' comes from the round-1 files restricted to the 500-doc subset;
    'veridian_r1' carries the full round-1 named/renamed pair (1,000 docs) for the renaming floor."""
    contract = {r["id"]: str(r["meta"]["contract_idx"]) for r in _rows(DATA / "cuad.jsonl")}
    out: dict = {}
    for f in RESULTS.glob("*/multi/*.jsonl"):
        arm = f.parts[-3]
        model, tag = parse_job_stem(f.stem)
        cond, _, rest = tag.partition("__")
        if "pilot" in rest:
            continue
        out[(arm, model, cond)] = _load_file(f, (lambda d: contract.get(d, d)) if arm == "cuad" else (lambda d: d))
    sub = {r["id"] for r in _rows(DATA / "veridian__para_subset.jsonl")} if (DATA / "veridian__para_subset.jsonl").exists() else set()
    for f in (R1_RESULTS / "veridian" / "multi").glob("*__named__all.jsonl"):
        model, _ = parse_job_stem(f.stem)
        rows = _load_file(f, lambda d: d)
        out[("veridian", model, "named")] = {k: v for k, v in rows.items() if k[0] in sub}
        out[("veridian_r1", model, "named")] = rows
    for f in (R1_RESULTS / "veridian" / "multi").glob("*__renamed__all.jsonl"):
        model, _ = parse_job_stem(f.stem)
        out[("veridian_r1", model, "renamed")] = _load_file(f, lambda d: d)
    return out


def _rows(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().split("\n") if l.strip()] if p.exists() else []


# ------------------------------------------------------------------------------------------------ bootstrap with a split

def boot_split(gold, a, b, clusters, mask, nb=B):
    """Δ(b − a) on mask and on ~mask in the same cluster resample; returns (Δmask, Δ~mask, Δmask − Δ~mask) each as (point, samples)."""
    nC = len(clusters)
    s_in, s_out = np.empty((nb, 4)), np.empty((nb, 4))
    for i in range(nb):
        idx = np.concatenate([clusters[j] for j in RNG.integers(0, nC, nC)])
        mi, mo = idx[mask[idx]], idx[~mask[idx]]
        s_in[i] = np.array(_prf_vec(gold[mi], b[mi])) - np.array(_prf_vec(gold[mi], a[mi]))
        s_out[i] = np.array(_prf_vec(gold[mo], b[mo])) - np.array(_prf_vec(gold[mo], a[mo]))
    p_in = np.array(_prf_vec(gold[mask], b[mask])) - np.array(_prf_vec(gold[mask], a[mask]))
    p_out = np.array(_prf_vec(gold[~mask], b[~mask])) - np.array(_prf_vec(gold[~mask], a[~mask]))
    return (_summ(p_in, s_in), s_in), (_summ(p_out, s_out), s_out), (_summ(p_in - p_out, s_in - s_out), s_in - s_out)


def _summ(point, samples) -> dict:
    out = {}
    for k, nm in enumerate(("precision", "recall", "f1", "accuracy")):
        col = samples[:, k]
        col = col[~np.isnan(col)]
        out[nm] = {"delta": None if np.isnan(point[k]) else float(point[k]), "lo": float(np.percentile(col, 2.5)) if len(col) else None,
                   "hi": float(np.percentile(col, 97.5)) if len(col) else None}
    return out


# ------------------------------------------------------------------------------------------------ pairs

def pair(rows, arm, model, cond_a, cond_b, doses: dict | None = None, dose_kind: str = "", nb=B) -> dict | None:
    A, Bm = rows.get((arm, model, cond_a), {}), rows.get((arm, model, cond_b), {})
    keys = sorted(set(A) & set(Bm))
    if not keys:
        return None
    gold = np.array([A[k]["gold"] for k in keys]); a = np.array([A[k]["pred"] for k in keys]); b = np.array([Bm[k]["pred"] for k in keys])
    ckeys = [(A[k]["cluster"], k[1]) for k in keys]
    clusters = _clusters(ckeys)
    res = {"n_pairs": len(keys), "n_docs": len({k[0] for k in keys}), "n_clusters": len(clusters), "conditions": (cond_a, cond_b),
           "cost_usd": {cond_a: sum(A[k]["cost"] for k in keys), cond_b: sum(Bm[k]["cost"] for k in keys)},
           cond_a: prf(gold, a), cond_b: prf(gold, b), "mcnemar": mcnemar(a == gold, b == gold), "flips": flips(gold, a, b),
           "label_changed_share": float((a != b).mean()), "topics": {}}
    res["delta"], samples = boot_delta(gold, a, b, clusters, nb=nb)
    res["_samples"] = samples
    topics = np.array([k[1] for k in keys])
    for t in sorted(set(topics)):
        ti = np.where(topics == t)[0]
        d, _ = boot_delta(gold[ti], a[ti], b[ti], _clusters([ckeys[i] for i in ti]), nb=400)
        res["topics"][t] = {"n": int(len(ti)), "n_pos": int(gold[ti].sum()), cond_a: prf(gold[ti], a[ti]), cond_b: prf(gold[ti], b[ti]), "delta": d,
                            "flips": flips(gold[ti], a[ti], b[ti]), "mcnemar": mcnemar(a[ti] == gold[ti], b[ti] == gold[ti])}
    if doses is not None:
        dose = np.array([doses.get(A[k]["cluster"] if dose_kind == "contract" else k[0], np.nan) for k in keys], dtype=float)
        res["dose"] = dose_response(gold, a, b, ckeys, dose, dose_kind)
    return res


def dose_response(gold, a, b, ckeys, dose, kind) -> dict:
    out: dict = {"kind": kind, "bands": {}}
    ok = ~np.isnan(dose)
    if kind == "contract":
        vals = np.unique(dose[ok])
        t1, t2 = np.percentile(vals, [33.3, 66.7]) if len(vals) >= 3 else (0, 0)
        bands = [("low", -1, t1), ("mid", t1, t2), ("high", t2, 9)]
        out["tercile_cuts"] = [float(t1), float(t2)]
        sel = lambda lo, hi: ok & (dose > lo) & (dose <= hi)  # noqa: E731
    else:
        bands = [("0", -1, 0), ("1-2", 0, 2), ("3+", 2, 10**9)]
        sel = lambda lo, hi: ok & (dose > lo) & (dose <= hi)  # noqa: E731
    for name, lo, hi in bands:
        di = np.where(sel(lo, hi))[0]
        if len(di) < 10:
            continue
        d, _ = boot_delta(gold[di], a[di], b[di], _clusters([ckeys[i] for i in di]), nb=500)
        out["bands"][name] = {"n": int(len(di)), "n_pos": int(gold[di].sum()), "n_clusters": len({ckeys[i][0] for i in di}), "delta": d, "flips": flips(gold[di], a[di], b[di])}
    # per-cluster Δaccuracy vs dose (Spearman)
    by: dict[str, list[int]] = defaultdict(list)
    for i, (c, _) in enumerate(ckeys):
        if ok[i]:
            by[c].append(i)
    xs, ys = [], []
    for c, idx in by.items():
        idx = np.array(idx)
        xs.append(float(dose[idx[0]]))
        ys.append(float(((b[idx] == gold[idx]).mean() - (a[idx] == gold[idx]).mean())))
    if len(xs) >= 8:
        from scipy.stats import spearmanr  # noqa: PLC0415

        rho, p = spearmanr(xs, ys)
        out["spearman"] = {"rho": float(rho), "p": float(p), "n_clusters": len(xs)}
    return out


# ------------------------------------------------------------------------------------------------ driver

def score_all(log=print) -> dict:
    rows = load_rows()
    models = [m for m in MODELS_ORDER if any(k[1] == m and k[0] in ("cuad", "jeb") for k in rows)]
    memo = json.loads((DATA / "cuad_memo.json").read_text()) if (DATA / "cuad_memo.json").exists() else {}
    dose_c = {ci: v for ci, v in memo.get("dose", {}).get("pooled", {}).items()}
    dose_j = {r["id"]: r["meta"].get("dose", 0) for r in _rows(DATA / "jeb.jsonl")}
    S: dict = {}
    summary: dict = {"models": models, "jev": JEV, "jev_present": JEV in models,
                     "jev_framing": "Jev's vendor states it is not pre-trained on these corpora; we treat that as a claim and test it.",
                     "arms": {"cuad": {"per_model": {}}, "veridian": {"per_model": {}}, "veridian_r1": {"per_model": {}}, "jeb": {"per_model": {}}},
                     "contrasts": {}, "cost": {}}
    for m in MODELS_ORDER:
        pm: dict = {}
        for cond in ("renamed", "paraphrased"):
            r = pair(rows, "cuad", m, "named", cond, dose_c, "contract")
            if r:
                S[("cuad", cond, m)] = r.pop("_samples")
                pm[cond] = r
                log(f"cuad {cond:11s} {m:14s} n={r['n_pairs']:5d} F1 {r['named']['f1']:.3f}→{r[cond]['f1']:.3f} Δ {r['delta']['f1']['delta']:+.3f} "
                    f"[{r['delta']['f1']['lo']:+.3f},{r['delta']['f1']['hi']:+.3f}] flips {r['flips']['right_to_wrong']}↓ {r['flips']['wrong_to_right']}↑ p={r['mcnemar']['p']:.3g}")
        summary["arms"]["cuad"]["per_model"][m] = pm or {"status": "missing"}
        r = pair(rows, "veridian", m, "named", "paraphrased")
        if r:
            S[("veridian", "paraphrased", m)] = r.pop("_samples")
            log(f"veridian paraphrased {m:14s} n={r['n_pairs']:5d} F1 {r['named']['f1']:.3f}→{r['paraphrased']['f1']:.3f} Δ {r['delta']['f1']['delta']:+.3f} [{r['delta']['f1']['lo']:+.3f},{r['delta']['f1']['hi']:+.3f}]")
        summary["arms"]["veridian"]["per_model"][m] = {"paraphrased": r} if r else {"status": "missing"}
        r = pair(rows, "veridian_r1", m, "named", "renamed")
        if r:
            S[("veridian_r1", "renamed", m)] = r.pop("_samples")
        summary["arms"]["veridian_r1"]["per_model"][m] = {"renamed": r} if r else {"status": "missing"}
        # Jeb: all topics, then the matter / control split within the same draws
        r = pair(rows, "jeb", m, "named", "renamed", dose_j, "doc")
        if r:
            A, Bm = rows[("jeb", m, "named")], rows[("jeb", m, "renamed")]
            keys = sorted(set(A) & set(Bm))
            gold = np.array([A[k]["gold"] for k in keys]); a = np.array([A[k]["pred"] for k in keys]); b = np.array([Bm[k]["pred"] for k in keys])
            ckeys = [(k[0], k[1]) for k in keys]
            mask = np.array([k[1] in JEB_MATTER for k in keys])
            (d_m, s_m), (d_c, s_c), (d_k, s_k) = boot_split(gold, a, b, _clusters(ckeys), mask)
            r.pop("_samples")
            r["matter"] = {"n_pairs": int(mask.sum()), "named": prf(gold[mask], a[mask]), "renamed": prf(gold[mask], b[mask]), "delta": d_m,
                           "flips": flips(gold[mask], a[mask], b[mask]), "mcnemar": mcnemar(a[mask] == gold[mask], b[mask] == gold[mask])}
            r["control"] = {"n_pairs": int((~mask).sum()), "named": prf(gold[~mask], a[~mask]), "renamed": prf(gold[~mask], b[~mask]), "delta": d_c,
                            "flips": flips(gold[~mask], a[~mask], b[~mask]), "mcnemar": mcnemar(a[~mask] == gold[~mask], b[~mask] == gold[~mask])}
            r["knowledge_effect"] = d_k
            S[("jeb", "matter", m)], S[("jeb", "control", m)] = s_m, s_c
            # dose bands on matter topics only (where names could carry knowledge)
            dose = np.array([dose_j.get(k[0], 0) for k in keys], dtype=float)
            mi = np.where(mask)[0]
            r["dose_matter"] = dose_response(gold[mi], a[mi], b[mi], [ckeys[i] for i in mi], dose[mi], "doc")
            log(f"jeb renamed {m:14s} n={r['n_pairs']:5d} ΔF1 all {r['delta']['f1']['delta']:+.3f}; matter {d_m['f1']['delta']:+.3f} [{d_m['f1']['lo']:+.3f},{d_m['f1']['hi']:+.3f}] "
                f"control {d_c['f1']['delta']:+.3f} [{d_c['f1']['lo']:+.3f},{d_c['f1']['hi']:+.3f}] effect {d_k['f1']['delta']:+.3f} [{d_k['f1']['lo']:+.3f},{d_k['f1']['hi']:+.3f}]")
        summary["arms"]["jeb"]["per_model"][m] = r or {"status": "missing"}
    # contrasts
    for m in MODELS_ORDER:
        c = summary["arms"]["cuad"]["per_model"].get(m, {})
        v = summary["arms"]["veridian"]["per_model"].get(m, {})
        v1 = summary["arms"]["veridian_r1"]["per_model"].get(m, {})
        j = summary["arms"]["jeb"]["per_model"].get(m, {})
        summary["contrasts"][m] = {
            "cuad_rename_minus_veridian_rename": contrast(S.get(("cuad", "renamed", m)), S.get(("veridian_r1", "renamed", m)), c.get("renamed", {}).get("delta"), (v1.get("renamed") or {}).get("delta")),
            "cuad_paraphrase_minus_veridian_paraphrase": contrast(S.get(("cuad", "paraphrased", m)), S.get(("veridian", "paraphrased", m)), c.get("paraphrased", {}).get("delta"), (v.get("paraphrased") or {}).get("delta")),
            "cuad_paraphrase_minus_cuad_rename": contrast(S.get(("cuad", "paraphrased", m)), S.get(("cuad", "renamed", m)), c.get("paraphrased", {}).get("delta"), c.get("renamed", {}).get("delta")),
            "jeb_matter_minus_control": j.get("knowledge_effect"),
            "jeb_all_minus_veridian_rename": contrast(S.get(("jeb", "matter", m)), S.get(("veridian_r1", "renamed", m)), (j.get("matter") or {}).get("delta"), (v1.get("renamed") or {}).get("delta")),
        }
    # auxiliary evidence
    summary["memo"] = memo.get("by_model_variant", {})
    summary["paraphrase"] = {}
    for arm in ("cuad", "veridian"):
        cache = _rows(DATA / f"{arm}__paraphrased.cache.jsonl")
        judge = _rows(DATA / f"{arm}_paraphrase_check.jsonl")
        if cache:
            summary["paraphrase"][arm] = {"n": len(cache), "checks_ok": sum(1 for r in cache if r["ok"]), "numbers_ok": sum(1 for r in cache if r["check"]["numbers_ok"]),
                                         "retried": sum(1 for r in cache if r["attempts"] > 1), "mean_ratio": round(sum(r["check"]["ratio"] for r in cache) / len(cache), 3),
                                         "mean_caps_recall": round(sum(r["check"]["caps_recall"] for r in cache) / len(cache), 3),
                                         "judge_n": len(judge), "judge_equivalent": sum(1 for r in judge if r["equivalent"]),
                                         "judge_examples": [{"id": r["id"], "differences": r["differences"][:2]} for r in judge if not r["equivalent"]][:4]}
    lp = RESULTS / "leak_check.jsonl"
    mapping = json.loads((DATA / "cuad_mapping.json").read_text()) if (DATA / "cuad_mapping.json").exists() else {}
    summary["leak"] = score_leak(_rows(lp), mapping) if lp.exists() else {}
    summary["build"] = json.loads((DATA / "round2_build.json").read_text()) if (DATA / "round2_build.json").exists() else {}
    # cost: estimate vs realised
    summary["cost"] = {"table": cost_table(log=lambda *_: None), "ledger": json.loads(SPEND.read_text()) if SPEND.exists() else {}}
    real = Counter()
    for (arm, m, cond), d in rows.items():
        if arm in ("cuad", "jeb") or (arm == "veridian" and cond == "paraphrased"):
            real[m] += sum(v["cost"] for v in d.values())
    summary["cost"]["realised_runs_by_model"] = {m: round(v, 3) for m, v in real.items()}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1, default=_json_default))
    log(f"wrote {RESULTS / 'summary.json'}")
    return summary


# ------------------------------------------------------------------------------------------------ report

def _d(d, k="f1"):
    if not d or not d.get(k) or d[k].get("delta") is None:
        return "–"
    x = d[k]
    s = f"{100*x['delta']:+.1f} [{100*x['lo']:+.1f}, {100*x['hi']:+.1f}]"
    return s + (" †" if (x["lo"] > 0 or x["hi"] < 0) else "")


def _f(v, nd=3):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def _mname(m):
    return {"gpt-5.6-luna": "GPT-5.6 Luna", "gpt-5.6-terra": "GPT-5.6 Terra", "gpt-5.6-sol": "GPT-5.6 Sol", JEV: "Jev"}.get(m, m)


def report_md(s: dict) -> str:
    models = s["models"]
    L = ["# Pseudonymisation ablation, round 2 — results", "",
         f"Systems under test: {', '.join(_mname(m) for m in models)}. {s['jev_framing']} † = 95 % CI excludes zero. "
         "Δ in F1 points (percentage points); cluster bootstrap (CUAD: by contract; others: by document), B = 2000.", ""]
    b = s.get("build", {})
    if b:
        L += [f"Data: CUAD {b['cuad']['n']} excerpts ({b['cuad']['positive_excerpts']} with a positive label, {b['cuad']['contracts']} contracts); "
              f"Veridian paraphrase control {b['veridian']['n']} e-mails; Jeb Bush {b['jeb']['n']} e-mails from {b['jeb']['source']} "
              f"(matter positives {sum(b['jeb']['positives_matter'].values())}, control positives {sum(b['jeb']['positives_control'].values())}).", ""]
    # A. CUAD
    L += ["## A. CUAD — rename and paraphrase", "", "| system | perturbation | n pairs | F1 named | F1 perturbed | ΔF1 [95% CI] | ΔRecall | ΔPrecision | right→wrong | wrong→right | McNemar p |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        pm = s["arms"]["cuad"]["per_model"].get(m, {})
        for cond in ("renamed", "paraphrased"):
            r = pm.get(cond)
            if not r:
                L.append(f"| {_mname(m)} | {cond} | – | – | – | missing | | | | | |")
                continue
            L.append(f"| {_mname(m)} | {cond} | {r['n_pairs']} | {_f(r['named']['f1'])} | {_f(r[cond]['f1'])} | {_d(r['delta'])} | {_d(r['delta'],'recall')} | {_d(r['delta'],'precision')} | "
                     f"{r['flips']['right_to_wrong']} | {r['flips']['wrong_to_right']} | {r['mcnemar']['p']:.3g} |")
    L += ["", "### Controls and knowledge effects (CUAD)", "", "| system | ΔF1 Veridian renamed (round 1, floor) | ΔF1 Veridian paraphrased (control) | rename effect: CUAD − Veridian | paraphrase effect: CUAD − Veridian | paraphrase − rename within CUAD |",
          "|---|---|---|---|---|---|"]
    for m in models:
        c = s["contrasts"].get(m, {})
        v1 = (s["arms"]["veridian_r1"]["per_model"].get(m, {}).get("renamed") or {}).get("delta")
        v = (s["arms"]["veridian"]["per_model"].get(m, {}).get("paraphrased") or {}).get("delta")
        L.append(f"| {_mname(m)} | {_d(v1)} | {_d(v)} | {_d(c.get('cuad_rename_minus_veridian_rename'))} | {_d(c.get('cuad_paraphrase_minus_veridian_paraphrase'))} | {_d(c.get('cuad_paraphrase_minus_cuad_rename'))} |")
    L += ["", "### Dose–response: ΔF1 by per-contract memorisation (finish-the-document LCS-F1 on the original text, pooled Luna/Terra/Sol; terciles over contracts)", "",
          "| system | perturbation | low tercile | mid | high | Spearman ρ (per-contract Δaccuracy vs dose) |", "|---|---|---|---|---|---|"]
    for m in models:
        pm = s["arms"]["cuad"]["per_model"].get(m, {})
        for cond in ("renamed", "paraphrased"):
            r = pm.get(cond)
            if not r or "dose" not in r:
                continue
            bands = r["dose"]["bands"]
            sp = r["dose"].get("spearman")
            L.append(f"| {_mname(m)} | {cond} | " + " | ".join(f"{_d(bands[k]['delta'])} (n={bands[k]['n']})" if k in bands else "–" for k in ("low", "mid", "high")) +
                     f" | {('ρ = %.2f, p = %.2f' % (sp['rho'], sp['p'])) if sp else '–'} |")
    if s.get("memo"):
        L += ["", "### What the perturbations do to verbatim retrievability (finish-the-document probe, 2 windows per contract, scored against the ORIGINAL continuation)", "",
              "| model | original: LCS-F1 / share ≥15-word run | renamed | paraphrased |", "|---|---|---|---|"]
        for m, d in s["memo"].items():
            cell = lambda v: f"{_f(v['lcs_f_vs_original'])} / {100*v['share_run15_vs_original']:.0f}%" if v else "–"  # noqa: E731
            L.append(f"| {_mname(m)} | {cell(d.get('original'))} | {cell(d.get('renamed'))} | {cell(d.get('paraphrased'))} |")
    if s.get("paraphrase"):
        L += ["", "### Paraphrase fidelity", ""]
        for arm, p in s["paraphrase"].items():
            L.append(f"- {arm}: {p['n']} documents; deterministic checks passed {p['checks_ok']}/{p['n']} (numbers preserved {p['numbers_ok']}, retried {p['retried']}); "
                     f"length ratio {p['mean_ratio']}, capitalised-term recall {p['mean_caps_recall']}; Terra fidelity judge: {p['judge_equivalent']}/{p['judge_n']} legally equivalent.")
    # B. Jeb
    L += ["", "## B. Jeb Bush — named vs renamed, matter topics vs control topics", "",
          f"Matter topics: {', '.join(JEB_MATTER)}. Control topics: {', '.join(JEB_CONTROL)}. Knowledge effect = Δ(matter) − Δ(control), paired within each bootstrap draw.", "",
          "| system | n pairs | ΔF1 all | ΔF1 matter [CI] | ΔF1 control [CI] | knowledge effect [CI] | ΔRecall matter | ΔPrecision matter | right→wrong | wrong→right | McNemar p (all) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        r = s["arms"]["jeb"]["per_model"].get(m, {})
        if not r or r.get("status") == "missing":
            L.append(f"| {_mname(m)} | – | missing | | | | | | | | |")
            continue
        L.append(f"| {_mname(m)} | {r['n_pairs']} | {_d(r['delta'])} | {_d(r['matter']['delta'])} | {_d(r['control']['delta'])} | {_d(r['knowledge_effect'])} | "
                 f"{_d(r['matter']['delta'],'recall')} | {_d(r['matter']['delta'],'precision')} | {r['flips']['right_to_wrong']} | {r['flips']['wrong_to_right']} | {r['mcnemar']['p']:.3g} |")
    L += ["", "### Per-topic ΔF1 (Jeb Bush)", "", "| topic | role | " + " | ".join(_mname(m) for m in models) + " |", "|---|---|" + "---|" * len(models)]
    for t in JEB_MATTER + JEB_CONTROL:
        cells = []
        for m in models:
            r = s["arms"]["jeb"]["per_model"].get(m, {})
            tt = (r.get("topics") or {}).get(t)
            cells.append(f"{_d(tt['delta'])} (pos {tt['n_pos']})" if tt else "–")
        L.append(f"| {t} | {'matter' if t in JEB_MATTER else 'control'} | " + " | ".join(cells) + " |")
    L += ["", "### Dose–response (Jeb Bush, matter topics): ΔF1 by mentions of public figures other than the Governor", "", "| system | 0 | 1–2 | 3+ |", "|---|---|---|---|"]
    for m in models:
        r = s["arms"]["jeb"]["per_model"].get(m, {})
        bands = (r.get("dose_matter") or {}).get("bands", {})
        if bands:
            L.append(f"| {_mname(m)} | " + " | ".join(f"{_d(bands[k]['delta'])} (n={bands[k]['n']})" if k in bands else "–" for k in ("0", "1-2", "3+")) + " |")
    if s.get("leak"):
        L += ["", "## Leakage checks (renamed documents; LLMs only — the identification question is generative)", ""]
        for arm, d in s["leak"].items():
            for m, v in d.items():
                extra = ("; by dose " + ", ".join(f"{b}: {x['identified']}/{x['n']}" for b, x in v["by_dose"].items())) if "by_dose" in v else ""
                L.append(f"- {arm} / {_mname(m)}: {v['identified']}/{v['n']} identified ({100*v['share']:.0f} %), {v['cannot_tell']} said they could not tell{extra}.")
    # cost
    ct = s["cost"]["table"]
    L += ["", "## Cost: estimated vs realised (paid, flex tier)", "", "| step | estimate | realised |", "|---|---|---|"]
    for st in s["cost"].get("ledger", {}).get("steps", []):
        L.append(f"| {st['step']} | {('$%.3f' % st['estimate_usd']) if st.get('estimate_usd') is not None else '–'} | ${st['realised_usd']:.3f} |")
    led = s["cost"].get("ledger", {})
    terra_ran = any(st["step"].startswith("run:") and st["step"].endswith(":gpt-5.6-terra") for st in led.get("steps", []))
    L += [f"| **total** | ${led.get('total_estimate_usd', 0):.2f} | **${led.get('total_realised_usd', 0):.2f}** |", "",
          f"Full version (all four systems incl. Terra) was estimated at ${ct['full_total_paid']:.2f} paid (${ct['openai_only_full']:.2f} on the OpenAI key); "
          + (f"the cheap version (Terra dropped) at ${ct['cheap']['total_paid']:.2f}. The cheap version was run first (2026-10-04); Terra was added afterwards, "
             f"so the full version is what is reported." if terra_ran else f"the version run (cheap: Terra dropped) at ${ct['cheap']['total_paid']:.2f}.")]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------------ figures

def _fig_html(svg: str, legend: str, title: str) -> str:
    from ..contam.html import CSS  # noqa: PLC0415

    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS} body{{background:#fff;margin:0;padding:18px 22px;width:760px}} "
            f"figure{{margin:0}} .legend{{margin-top:6px}}</style></head><body>{svg}{legend}</body></html>")


def _png(html_text: str, out: Path, width: int = 804, height: int = 420) -> bool:
    chrome = next((p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and Path(p).exists()), None)
    if not chrome:
        return False
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "fig.html"
        src.write_text(html_text)
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}", "--force-device-scale-factor=2",
                        f"--screenshot={out}", src.as_uri()], check=False, capture_output=True, timeout=120)
    return out.exists()


def make_figures(s: dict, log=print) -> list[Path]:
    from ..contam.html import MODEL_META, dotplot, legend  # noqa: PLC0415
    from .report import deltaplot  # noqa: PLC0415  (registers Jev colour)

    models = s["models"]
    out = []
    vals = lambda get: {m: (lambda d: (d["delta"], d["lo"], d["hi"]) if d and d.get("delta") is not None else None)((get(m) or {}).get("f1")) for m in models}  # noqa: E731
    # Big Thorium (Relativity's public demo workspace, invented case) is a second renaming floor beside Veridian when its arm has been run
    bt_path = RESULTS.parent / "bigthorium" / "summary.json"
    bt = json.loads(bt_path.read_text()).get("rename", {}) if bt_path.exists() else {}
    bt_row = [("bt_ren", vals(lambda m: (bt.get(m) or {}).get("delta")))] if bt else []
    bt_lbl = {"bt_ren": "ΔF1 Big Thorium, renamed (2nd floor)"}
    # A — CUAD
    rows = [("cuad_ren", vals(lambda m: (s["arms"]["cuad"]["per_model"].get(m, {}).get("renamed") or {}).get("delta"))),
            ("ver_ren", vals(lambda m: (s["arms"]["veridian_r1"]["per_model"].get(m, {}).get("renamed") or {}).get("delta")))] + bt_row + [
            ("eff_ren", vals(lambda m: s["contrasts"].get(m, {}).get("cuad_rename_minus_veridian_rename"))),
            ("cuad_par", vals(lambda m: (s["arms"]["cuad"]["per_model"].get(m, {}).get("paraphrased") or {}).get("delta"))),
            ("ver_par", vals(lambda m: (s["arms"]["veridian"]["per_model"].get(m, {}).get("paraphrased") or {}).get("delta"))),
            ("eff_par", vals(lambda m: s["contrasts"].get(m, {}).get("cuad_paraphrase_minus_veridian_paraphrase")))]
    labels = {"cuad_ren": "ΔF1 CUAD, renamed", "ver_ren": "ΔF1 Veridian, renamed (floor)", "eff_ren": "Rename knowledge effect",
              "cuad_par": "ΔF1 CUAD, paraphrased", "ver_par": "ΔF1 Veridian, paraphrased (control)", "eff_par": "Paraphrase knowledge effect", **bt_lbl}
    roles = {"eff_ren": "effect", "eff_par": "effect", "ver_ren": "floor", "ver_par": "floor", "bt_ren": "public-invented"}
    allv = [abs(v[0]) for _, d in rows for v in d.values() if v] + [abs(v[1]) for _, d in rows for v in d.values() if v] + [abs(v[2]) for _, d in rows for v in d.values() if v]
    lim = max(0.06, math.ceil(max(allv + [0.05]) * 100 / 2) * 2 / 100)
    fig = deltaplot(rows, models, "CUAD: effect of renaming / paraphrasing on F1, and the knowledge effect net of the Veridian control (F1 points, 95 % CI)",
                    labels, roles=roles, xmin=-lim, xmax=lim, width=760, label_w=250, step=2 if lim <= 0.12 else 4,
                    note="Knowledge effect = Δ(CUAD) − Δ(Veridian), difference of cluster-bootstrap distributions. Veridian is a fictional matter no model can have seen."
                         + (" Big Thorium (Relativity's public aiR demo workspace, fictional case) is shown as a second floor; it is not subtracted." if bt else ""))
    p = RESULTS / "fig_cuad.png"
    if _png(_fig_html(fig, legend(models), "cuad"), p, height=120 + 12 * len(models) * len(rows) + 14 * len(rows) + 80):
        out.append(p)
    # B — Jeb
    rows = [("matter", vals(lambda m: (s["arms"]["jeb"]["per_model"].get(m, {}).get("matter") or {}).get("delta"))),
            ("control", vals(lambda m: (s["arms"]["jeb"]["per_model"].get(m, {}).get("control") or {}).get("delta"))),
            ("effect", vals(lambda m: s["arms"]["jeb"]["per_model"].get(m, {}).get("knowledge_effect"))),
            ("ver_ren", vals(lambda m: (s["arms"]["veridian_r1"]["per_model"].get(m, {}).get("renamed") or {}).get("delta")))] + bt_row
    labels = {"matter": "ΔF1 matter topics (renamed − named)", "control": "ΔF1 control topics", "effect": "Knowledge effect (matter − control)", "ver_ren": "ΔF1 Veridian, renamed (floor)", **bt_lbl}
    allv = [abs(x) for _, d in rows for v in d.values() if v for x in v]
    lim = max(0.06, math.ceil(max(allv + [0.05]) * 100 / 2) * 2 / 100)
    fig = deltaplot(rows, models, "Jeb Bush e-mails: renaming the Governor and Florida's public figures — matter topics vs control topics (F1 points, 95 % CI)",
                    labels, roles={"effect": "effect", "ver_ren": "floor", "bt_ren": "public-invented"}, xmin=-lim, xmax=lim, width=760, label_w=250, step=2 if lim <= 0.12 else 4,
                    note="Matter topics: 2000 recount, Rilya Wilson, Medicaid reform, George W. Bush, Terri Schiavo. Control: movie gallery, condominiums, bottled water, marketing, faith-based, NRA ×2. Same documents, same draws.")
    p = RESULTS / "fig_jeb.png"
    if _png(_fig_html(fig, legend(models), "jeb"), p, height=120 + 12 * len(models) * len(rows) + 14 * len(rows) + 80):
        out.append(p)
    for p in out:
        log(f"figure {p}")
    return out


def write_report(summary: dict, figures: bool = True, log=print) -> list[Path]:

    (RESULTS / "REPORT.md").write_text(report_md(summary))
    out = [RESULTS / "summary.json", RESULTS / "REPORT.md"]
    if figures:
        out += make_figures(summary, log=log)
    return out

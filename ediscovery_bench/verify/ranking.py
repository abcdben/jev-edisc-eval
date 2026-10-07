"""Check B — ranking stability across known and unknown matters (existing results only; no API calls).

Two system × corpus tables are built from saved predictions, each scored on exactly the documents the systems share:

  four-system table   Luna / Terra / Sol / Jev on Enron J (ablation, named, knowledge requests), Enron K (ablation, named),
                      Mallinckrodt (ablation, no brief), Veridian (ablation, named) and Endo (results/endo)
  roster table        the main study's results/<corpus>/multi files for Jeb Bush, Mallinckrodt, CUAD, Veridian (Luna, Terra, Jev,
                      Claude Sonnet 5, Gemini 3.8 Flash; Haiku / Flash-Lite where present) — adds the two corpora Sol never ran

For each table: F1 / recall / precision per cell, the rank order of systems per corpus, Kendall's W across corpora (corpora as
judges, systems as objects; χ² approximation — with n = 4 systems W has little power, stated plainly), pairwise Spearman between
corpus rankings, and F1 against the corpus's case-knowledge composite (`results/contam/summary.json → composite.case_score`,
Veridian = 0, Enron K carries Enron's score but its requests are knowledge-poor and it is flagged). Difficulty proxies: mean pairwise
Cohen κ between the systems on the corpus, the gray share, and the human-disagreement figures the explore index carries.

Gold caveats carried into the summary: Endo's gold is a Luna + Terra + Sol panel (their Endo F1 is partly circular); Mallinckrodt's
is a Sonnet 5 + Terra + Gemini 3.8 Flash panel (same for those three); Veridian's is the synthetic planner's; Enron and Jeb Bush are
human (TREC); CUAD is the annotators'.
"""
from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations

import numpy as np

from ..runner import load_predictions
from ..tasks import TaskSet
from .common import JEV, LUNA, POS, ROOT, SOL, TERRA, kendall_w, prf, spearman

ABL = ROOT / "results" / "ablation"
CONTAM = ROOT / "results" / "contam" / "summary.json"
EXPLORE_INDEX = ROOT / "site" / "public" / "explore" / "index.json"
ENRON_J_TOPICS = ["prepay_transactions", "fas140", "financial_forecasts", "document_destruction", "energy_schedules", "financial_analysts"]

CORPORA = {
    # key: (label, contam dataset, exposure group, task yaml, explore id, gold note)
    "enron_j": ("Enron — Complaint J", "enron", "known", "tasks/enron_j.yaml", "legal10-learn", "human (TREC Legal 2010 learning-task assessors)"),
    "enron_k": ("Enron — Complaint K", "enron", "known mailbox, knowledge-poor requests", "tasks/enron_k.yaml", "legal10", "human (TREC Legal 2010, Topic Authority adjudicated)"),
    "jebbush": ("Jeb Bush (TREC 2016)", "jebbush", "known", "tasks/trec.yaml", "trec", "human (NIST assessors)"),
    "mnk": ("Mallinckrodt", "mnk", "less known", "tasks/mallinckrodt.yaml", "mnk", "LLM panel: Sonnet 5 + Terra + Gemini 3.8 Flash (circular for those three)"),
    "endo": ("Endo (post-cutoff documents)", "endo", "less known", "tasks/endo.yaml", "endo", "LLM panel: Luna + Terra + Sol (circular for those three)"),
    "cuad": ("CUAD contracts", "cuad", "benchmark (no case channels)", "tasks/cuad.yaml", "cuad", "human (CUAD annotators)"),
    "veridian": ("Veridian (synthetic)", "veridian", "unknown", "tasks/veridian.yaml", "veridian", "synthetic planner gold"),
}
FOUR = [LUNA, TERRA, SOL, JEV]
ROSTER = [LUNA, TERRA, JEV, "claude-sonnet-5", "gemini-3.8-flash", "claude-haiku-4.5", "gemini-3.5-flash-lite"]
ROSTER_CORE = [LUNA, TERRA, JEV, "claude-sonnet-5", "gemini-3.8-flash"]
PANEL_MEMBERS = {"endo": {LUNA, TERRA, SOL}, "mnk": {TERRA, "claude-sonnet-5", "gemini-3.8-flash"}}


# ------------------------------------------------------------------------------------------------ loading

def _rows(path, qids: set[str] | None) -> dict[tuple[str, str], tuple[int, int, bool]]:
    out = {}
    for p in load_predictions(path):
        if p.error or p.gold is None or not p.label or (qids is not None and p.question not in qids):
            continue
        out[(p.doc_id, p.question)] = (1 if p.gold == POS else 0, 1 if p.label == POS else 0, bool(p.gray))
    return out


def _ablation_named(arm: str, model: str) -> dict:
    out = {}
    stem = model.replace("@", "__")
    for f in (ABL / arm / "multi").glob(f"{stem}__named__*.jsonl"):
        out.update(_rows(f, set(ENRON_J_TOPICS) if arm == "enron_j" else None))
    return out


def _study(corpus: str, model: str) -> dict:
    qids = set(TaskSet.load(ROOT / CORPORA[corpus][3]).qids)
    f = ROOT / "results" / corpus / "multi" / f"{model.replace('@', '__')}.jsonl"
    return _rows(f, qids) if f.exists() else {}


def _dir_study(corpus: str) -> str:
    return {"jebbush": "trec"}.get(corpus, corpus)


def load_table(which: str) -> dict[str, dict[str, dict]]:
    """which = 'four' | 'roster' → {corpus: {model: rows}} (rows keyed by (doc, question))."""
    out: dict[str, dict[str, dict]] = {}
    if which == "four":
        for arm in ("enron_j", "enron_k", "mnk", "veridian"):
            out[arm] = {m: r for m in FOUR if (r := _ablation_named(arm, m))}
        out["endo"] = {m: r for m in FOUR if (r := _rows(ROOT / "results" / "endo" / "multi" / f"{m.replace('@', '__')}.jsonl", set(TaskSet.load(ROOT / "tasks/endo.yaml").qids)))}
    else:
        for c in ("jebbush", "mnk", "cuad", "veridian", "endo"):
            d = _dir_study(c)
            qids = set(TaskSet.load(ROOT / CORPORA[c][3]).qids)
            out[c] = {m: r for m in ROSTER + [SOL] if (f := ROOT / "results" / d / "multi" / f"{m.replace('@', '__')}.jsonl").exists() and (r := _rows(f, qids))}
    return {c: ms for c, ms in out.items() if ms}


# ------------------------------------------------------------------------------------------------ scoring

def _kappa(a: np.ndarray, b: np.ndarray) -> float:
    po = (a == b).mean()
    pe = (a.mean() * b.mean()) + ((1 - a.mean()) * (1 - b.mean()))
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def score_table(table: dict[str, dict[str, dict]], systems: list[str], exclude_gray: bool = False) -> dict:
    cells: dict[str, dict[str, dict]] = {}
    difficulty: dict[str, dict] = {}
    for corpus, ms in table.items():
        present = [m for m in systems if m in ms]
        if len(present) < 2:
            continue
        keys = set.intersection(*(set(ms[m]) for m in present))
        if exclude_gray:
            keys = {k for k in keys if not ms[present[0]][k][2]}
        keys = sorted(keys)
        if not keys:
            continue
        gold = np.array([ms[present[0]][k][0] for k in keys])
        preds = {m: np.array([ms[m][k][1] for k in keys]) for m in present}
        cells[corpus] = {}
        for m in present:
            cells[corpus][m] = {**prf(gold, preds[m]), "panel_member": m in PANEL_MEMBERS.get(corpus, set())}
        kappas = [_kappa(preds[a], preds[b]) for a, b in combinations(present, 2)]
        difficulty[corpus] = {"n": len(keys), "n_docs": len({k[0] for k in keys}), "prevalence": float(gold.mean()),
                              "gray_share": float(np.mean([ms[present[0]][k][2] for k in keys])) if not exclude_gray else 0.0,
                              "mean_pairwise_kappa": float(np.mean(kappas)), "mean_f1": float(np.nanmean([cells[corpus][m]["f1"] for m in present])),
                              "systems": present}
    return {"cells": cells, "difficulty": difficulty}


def rank_block(cells: dict[str, dict[str, dict]], systems: list[str], metric: str = "f1") -> dict:
    """Ranks per corpus over the systems present on every listed corpus; Kendall's W; pairwise Spearman."""
    corpora = [c for c in cells if all(m in cells[c] for m in systems)]
    if len(corpora) < 2:
        return {"corpora": corpora, "note": "fewer than two corpora with all systems"}
    matrix = [[cells[c][m][metric] for m in systems] for c in corpora]
    ranks = {}
    for c, row in zip(corpora, matrix):
        order = sorted(range(len(systems)), key=lambda i: -row[i])
        ranks[c] = [systems[i] for i in order]
    pair = {}
    for a, b in combinations(range(len(corpora)), 2):
        s = spearman(matrix[a], matrix[b])
        pair[f"{corpora[a]} vs {corpora[b]}"] = {"rho": s["rho"], "p_perm": s["p"]}
    w = kendall_w(matrix)
    return {"systems": systems, "corpora": corpora, "metric": metric, "matrix": matrix, "ranking": ranks, "kendall_w": w, "pairwise_spearman": pair,
            "top_system_per_corpus": {c: ranks[c][0] for c in corpora}}


def case_scores() -> dict[str, dict[str, float | None]]:
    """model -> corpus -> case_score (0–100) from the contamination composite; Veridian 0; Jev not testable."""
    comp = json.loads(CONTAM.read_text())["composite"]["per_model"] if CONTAM.exists() else {}
    out: dict[str, dict[str, float | None]] = {}
    for m, ds in comp.items():
        out[m] = {}
        for corpus, (_, cds, _, _, _, _) in CORPORA.items():
            v = (ds.get(cds) or {}).get("case_score")
            out[m][corpus] = 0.0 if corpus == "veridian" else v
    return out


def trend_block(cells: dict, systems: list[str], cs: dict, llms: list[str]) -> dict:
    """F1 and difficulty-adjusted F1 (F1 − mean F1 of the systems on that corpus) against case knowledge, per LLM; the LLM-vs-Jev
    gap against the mean LLM case score. Enron K and CUAD are excluded from the trend (knowledge-poor requests / no case channels)."""
    use = [c for c in cells if c not in ("enron_k", "cuad")]
    out: dict = {"corpora": use, "per_model": {}, "llm_minus_jev": {}}
    for m in llms:
        xs, ys, ya = [], [], []
        for c in use:
            if m not in cells[c] or cs.get(m, {}).get(c) is None:
                continue
            present = [s for s in systems if s in cells[c]]
            mean_f1 = float(np.nanmean([cells[c][s]["f1"] for s in present]))
            xs.append(cs[m][c]); ys.append(cells[c][m]["f1"]); ya.append(cells[c][m]["f1"] - mean_f1)
        if len(xs) >= 3:
            out["per_model"][m] = {"n": len(xs), "case_scores": xs, "f1": ys, "f1_adjusted": ya, "spearman_f1": spearman(xs, ys), "spearman_f1_adjusted": spearman(xs, ya)}
    # LLM − Jev gap vs the LLMs' mean case score on the corpus
    xs, ys, labels = [], [], []
    for c in use:
        if JEV not in cells[c]:
            continue
        ll = [m for m in llms if m in cells[c] and cs.get(m, {}).get(c) is not None]
        if not ll:
            continue
        xs.append(float(np.mean([cs[m][c] for m in ll]))); ys.append(float(np.mean([cells[c][m]["f1"] for m in ll]) - cells[c][JEV]["f1"])); labels.append(c)
    if len(xs) >= 3:
        out["llm_minus_jev"] = {"corpora": labels, "mean_llm_case_score": xs, "gap_f1": ys, "spearman": spearman(xs, ys)}
    return out


def human_disagreement() -> dict:
    """Human-disagreement proxies from the explore index (contested / n), where the dataset has one."""
    if not EXPLORE_INDEX.exists():
        return {}
    idx = json.loads(EXPLORE_INDEX.read_text())
    by = {d["id"]: d for d in idx["datasets"]}
    out = {}
    for corpus, (_, _, _, _, eid, _) in CORPORA.items():
        d = by.get(eid)
        if not d:
            continue
        n = sum(t.get("n") or 0 for t in d["topics"]); con = sum(t.get("n_contested") or 0 for t in d["topics"]); gray = sum(t.get("n_gray") or 0 for t in d["topics"])
        out[corpus] = {"explore_id": eid, "n": n, "contested": con, "contested_share": con / n if n else None, "gray_share": gray / n if n else None,
                       "humans": [h["name"] for h in d.get("humans", [])]}
    alt = by.get("trec-alt")
    if alt:
        n = sum(t.get("n") or 0 for t in alt["topics"]); con = sum(t.get("n_contested") or 0 for t in alt["topics"])
        out["jebbush"]["alternate_assessor_disagreement"] = {"n": n, "contested": con, "share": con / n if n else None}
    return out


def score(log=print) -> dict:
    cs = case_scores()
    out: dict = {"corpora": {c: {"label": v[0], "exposure": v[2], "gold": v[5]} for c, v in CORPORA.items()}, "case_scores": cs,
                 "human_disagreement": human_disagreement(), "tables": {}}
    for which, systems, core in (("four", FOUR, FOUR), ("roster", ROSTER, ROSTER_CORE)):
        table = load_table(which)
        blk: dict = {}
        for gray_mode in ("all_gold", "gray_excluded"):
            sc = score_table(table, systems, exclude_gray=(gray_mode == "gray_excluded"))
            blk[gray_mode] = {**sc, "ranks_f1": rank_block(sc["cells"], core, "f1"), "ranks_recall": rank_block(sc["cells"], core, "recall"),
                              "ranks_precision": rank_block(sc["cells"], core, "precision")}
            if which == "four":
                # W without the panel-circular Endo cell and without the knowledge-poor Enron K
                sub = {c: v for c, v in sc["cells"].items() if c not in ("endo",)}
                blk[gray_mode]["ranks_f1_without_endo"] = rank_block(sub, core, "f1")
                sub2 = {c: v for c, v in sc["cells"].items() if c not in ("endo", "enron_k")}
                blk[gray_mode]["ranks_f1_without_endo_enron_k"] = rank_block(sub2, core, "f1")
            blk[gray_mode]["trend"] = trend_block(sc["cells"], core, cs, [m for m in (LUNA, TERRA, SOL) if m in core])
        out["tables"][which] = blk
        cells = blk["all_gold"]["cells"]
        for c in cells:
            log(f"B [{which}] {c:9s} " + "  ".join(f"{m.split('@')[0][:12]:>12s} F1 {cells[c][m]['f1']:.3f}" for m in systems if m in cells[c]))
        rk = blk["all_gold"]["ranks_f1"]
        if "kendall_w" in rk:
            log(f"B [{which}] Kendall W (F1) = {rk['kendall_w']['W']:.3f} over {len(rk['corpora'])} corpora × {len(core)} systems; p≈{rk['kendall_w']['p_approx']:.3f}")
    return out

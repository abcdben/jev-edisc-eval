"""Paths, the OpenAI spend ledger / cap, and statistics shared by the four checks.

The statistics (Wilson, bootstrap, paired bootstrap, exact McNemar) are the ones used by the classifier-native tests
(`jevprobe.common`); they are imported rather than re-implemented so every write-up uses the same arithmetic.
"""
from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import numpy as np

from ..jevprobe.common import (JEV, LLMS, LUNA, SOL, TERRA, append_jsonl, bootstrap_ci, fmt_ci_pp, fmt_pct, fmt_pp, mcnemar, paired_diff,
                               read_jsonl, wilson, write_jsonl)

__all__ = ["JEV", "LLMS", "LUNA", "SOL", "TERRA", "append_jsonl", "bootstrap_ci", "fmt_ci_pp", "fmt_pct", "fmt_pp", "mcnemar", "paired_diff",
           "read_jsonl", "wilson", "write_jsonl", "ROOT", "DATA", "RESULTS", "LEDGER", "SEED", "SYSTEMS", "POS", "CAP_USD", "ledger_add",
           "ledger_total", "prediction_spend", "openai_spend", "prf", "boot_delta_by_cluster", "indep_diff", "kendall_w", "spearman"]

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "verify"
RESULTS = ROOT / "results" / "verify"
LEDGER = RESULTS / "llm_spend.jsonl"   # non-prediction OpenAI calls (the Check A tagger)
SEED = 31
SYSTEMS = [LUNA, TERRA, SOL, JEV]
POS = "responsive"
CAP_USD = 15.0                          # total NEW OpenAI spend (paid, i.e. flex) across A + C + D


# ------------------------------------------------------------------------------------------------ spend

def ledger_add(step: str, model: str, cost_usd: float, n_calls: int = 1, note: str = "") -> None:
    append_jsonl(LEDGER, {"step": step, "model": model, "cost_usd": round(cost_usd, 6), "n_calls": n_calls, "note": note})


def ledger_total(steps: Sequence[str] | None = None) -> float:
    return sum(r["cost_usd"] for r in read_jsonl(LEDGER) if steps is None or r["step"] in steps)


def prediction_spend(check: str, models: Sequence[str] | None = None, list_price: bool = False) -> float:
    """Paid (or list) cost of every prediction row under results/verify/<check>/multi/ for the given models (OpenAI by default)."""
    d = RESULTS / check / "multi"
    total = 0.0
    for f in d.glob("*.jsonl") if d.exists() else []:
        stem_model = f.stem.split("__")[0]
        if models is not None and stem_model not in models:
            continue
        if models is None and not stem_model.startswith("gpt-"):
            continue
        for r in read_jsonl(f):
            total += float(r.get("list_cost_usd" if list_price else "cost_usd") or 0.0)
    return total


def openai_spend() -> dict:
    a = ledger_total(["a_tag"])
    c = prediction_spend("c")
    d = prediction_spend("d")
    return {"a_tagging": round(a, 4), "c_predictions": round(c, 4), "d_predictions": round(d, 4), "total": round(a + c + d, 4),
            "c_list": round(prediction_spend("c", list_price=True), 4), "d_list": round(prediction_spend("d", list_price=True), 4),
            "jev_c": round(prediction_spend("c", ["jev"]), 4), "jev_d": round(prediction_spend("d", ["jev"]), 4), "cap": CAP_USD}


# ------------------------------------------------------------------------------------------------ metrics

def prf(gold: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(((gold == 1) & (pred == 1)).sum()); fp = int(((gold == 0) & (pred == 1)).sum())
    fn = int(((gold == 1) & (pred == 0)).sum()); tn = int(((gold == 0) & (pred == 0)).sum())
    P = tp / (tp + fp) if tp + fp else float("nan")
    R = tp / (tp + fn) if tp + fn else float("nan")
    F = 2 * P * R / (P + R) if (tp + fp and tp + fn and P + R) else (0.0 if tp + fn else float("nan"))
    return {"n": int(len(gold)), "pos": tp + fn, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": P, "recall": R, "f1": F,
            "accuracy": (tp + tn) / len(gold) if len(gold) else float("nan")}


def _vec(gold, pred):
    tp = ((gold == 1) & (pred == 1)).sum(); fp = ((gold == 0) & (pred == 1)).sum(); fn = ((gold == 1) & (pred == 0)).sum()
    P = tp / (tp + fp) if tp + fp else np.nan
    R = tp / (tp + fn) if tp + fn else np.nan
    F = 2 * P * R / (P + R) if (tp + fp and tp + fn and (P + R) > 0) else (0.0 if tp + fn else np.nan)
    return np.array([P, R, F, (gold == pred).mean()])


METRICS = ("precision", "recall", "f1", "accuracy")


def boot_delta_by_cluster(gold: np.ndarray, a: np.ndarray, b: np.ndarray, cluster_ids: Sequence, nb: int = 2000, seed: int = SEED) -> tuple[dict, np.ndarray]:
    """metric(b) − metric(a) with a cluster (document) bootstrap; returns ({metric: {delta, lo, hi}}, samples[nb, 4]).
    Also returns the point metrics of each condition under "a" / "b" keys."""
    by = defaultdict(list)
    for i, c in enumerate(cluster_ids):
        by[c].append(i)
    clusters = [np.array(v) for v in by.values()]
    rng = np.random.default_rng(seed)
    point = _vec(gold, b) - _vec(gold, a)
    samples = np.empty((nb, 4))
    nC = len(clusters)
    for i in range(nb):
        pick = rng.integers(0, nC, nC)
        idx = np.concatenate([clusters[j] for j in pick])
        samples[i] = _vec(gold[idx], b[idx]) - _vec(gold[idx], a[idx])
    out = {}
    for k, nm in enumerate(METRICS):
        col = samples[:, k]; col = col[~np.isnan(col)]
        out[nm] = {"delta": None if np.isnan(point[k]) else float(point[k]),
                   "lo": float(np.percentile(col, 2.5)) if len(col) else None, "hi": float(np.percentile(col, 97.5)) if len(col) else None}
    return out, samples


def indep_diff(sa: np.ndarray, sb: np.ndarray, pa: dict, pb: dict) -> dict:
    """Difference of two independent bootstrap delta distributions (a − b) per metric."""
    n = min(len(sa), len(sb))
    out = {}
    for k, nm in enumerate(METRICS):
        d = sa[:n, k] - sb[:n, k]; d = d[~np.isnan(d)]
        da, db = pa[nm]["delta"], pb[nm]["delta"]
        out[nm] = {"delta": (da - db) if da is not None and db is not None else None,
                   "lo": float(np.percentile(d, 2.5)) if len(d) else None, "hi": float(np.percentile(d, 97.5)) if len(d) else None}
    return out


# ------------------------------------------------------------------------------------------------ rank statistics

def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: -values[i])  # rank 1 = largest
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def kendall_w(matrix: Sequence[Sequence[float]]) -> dict:
    """Kendall's W over m judges (rows: corpora) ranking n objects (columns: systems) by the row values. Chi-square approx p."""
    m, n = len(matrix), len(matrix[0])
    R = [sum(_ranks(row)[j] for row in matrix) for j in range(n)]
    Rbar = sum(R) / n
    S = sum((r - Rbar) ** 2 for r in R)
    # tie correction
    T = 0.0
    for row in matrix:
        from collections import Counter

        for c in Counter(row).values():
            T += c ** 3 - c
    denom = m * m * (n ** 3 - n) - m * T
    W = 12 * S / denom if denom else float("nan")
    chi2 = m * (n - 1) * W
    # chi-square survival with df = n-1 (small df; use the regularised gamma via math)
    p = _chi2_sf(chi2, n - 1)
    return {"W": W, "m_judges": m, "n_objects": n, "chi2": chi2, "df": n - 1, "p_approx": p, "mean_ranks": R}


def _chi2_sf(x: float, k: int) -> float:
    if x != x or x <= 0:
        return 1.0
    # regularised upper incomplete gamma Q(k/2, x/2) via series/continued fraction (Numerical Recipes gammq)
    a, z = k / 2.0, x / 2.0

    def gser(a, z):
        s = t = 1.0 / a
        ap = a
        for _ in range(500):
            ap += 1; t *= z / ap; s += t
            if abs(t) < abs(s) * 1e-14:
                break
        return s * math.exp(-z + a * math.log(z) - math.lgamma(a))

    def gcf(a, z):
        b = z + 1 - a; c = 1e300; d = 1 / b; h = d
        for i in range(1, 500):
            an = -i * (i - a); b += 2
            d = an * d + b; d = 1e-300 if abs(d) < 1e-300 else d
            c = b + an / c; c = 1e-300 if abs(c) < 1e-300 else c
            d = 1 / d; de = d * c; h *= de
            if abs(de - 1) < 1e-14:
                break
        return math.exp(-z + a * math.log(z) - math.lgamma(a)) * h

    return (1 - gser(a, z)) if z < a + 1 else gcf(a, z)


def spearman(x: Sequence[float], y: Sequence[float]) -> dict:
    n = len(x)
    if n < 3:
        return {"rho": float("nan"), "n": n, "p": float("nan")}
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx); vy = sum((b - my) ** 2 for b in ry)
    rho = cov / math.sqrt(vx * vy) if vx and vy else float("nan")
    # permutation p (exact for small n)
    rng = random.Random(SEED)
    perms = 0; hits = 0
    for _ in range(5000):
        p = ry[:]; rng.shuffle(p)
        c = sum((a - mx) * (b - my) for a, b in zip(rx, p))
        r = c / math.sqrt(vx * vy) if vx and vy else 0
        perms += 1; hits += abs(r) >= abs(rho) - 1e-12
    return {"rho": rho, "n": n, "p": hits / perms}


def jsonable(o):
    if isinstance(o, dict):
        return {k: jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        o = o.item()
    if isinstance(o, float) and math.isnan(o):
        return None
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    return o


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(obj), indent=1, ensure_ascii=False))

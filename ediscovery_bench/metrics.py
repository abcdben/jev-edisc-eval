"""Per-question and pooled metrics for binary responsiveness predictions.

All metrics are computed twice: on all gold-labeled docs and excluding docs
whose gold for that question is flagged gray.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import sqrt

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    cohen_kappa_score,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .providers import Prediction


@dataclass
class QMetrics:
    question: str
    n: int
    n_pos: int
    n_errors: int
    precision: float | None = None
    recall: float | None = None
    recall_ci: tuple[float, float] | None = None
    f1: float | None = None
    specificity: float | None = None
    elusion: float | None = None
    kappa: float | None = None
    accuracy: float | None = None
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    roc_auc: float | None = None
    pr_auc: float | None = None
    brier: float | None = None
    log_loss: float | None = None
    ece: float | None = None
    best_f1: float | None = None
    best_f1_threshold: float | None = None
    recall_targets: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class OpMetrics:
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    input_tokens_mean: float
    output_tokens_mean: float
    cached_tokens_mean: float
    total_cost_usd: float
    total_list_cost_usd: float
    cost_per_1k_docs_usd: float  # per 1k (doc, question) decisions
    pricing_modes: dict[str, int]

    def to_dict(self):
        return asdict(self)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def ece_score(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        m = (p >= lo) & (p <= hi) if i == 0 else (p > lo) & (p <= hi)
        if m.sum():
            e += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(e)


def recall_targets(y: np.ndarray, p: np.ndarray, targets=(0.75, 0.80, 0.90, 0.95)) -> dict:
    out = {}
    n_pos = int(y.sum())
    if n_pos == 0:
        return out
    order = np.argsort(-p, kind="stable")
    ps, ys = p[order], y[order]
    cum = np.cumsum(ys)
    for t in targets:
        idx = int(np.argmax(cum >= t * n_pos))
        if cum[idx] < t * n_pos:
            continue
        k = idx + 1
        out[f"recall@{int(t*100)}"] = {
            "threshold": float(ps[idx]),
            "precision": float(cum[idx] / k),
            "recall": float(cum[idx] / n_pos),
            "review_fraction": float(k / len(y)),
        }
    return out


def best_f1(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    best, thr = 0.0, 0.5
    for t in np.unique(np.round(p, 3)):
        yhat = (p >= t).astype(int)
        f = f1_score(y, yhat, zero_division=0)
        if f > best:
            best, thr = float(f), float(t)
    return best, thr


def question_metrics(qid: str, preds: list[Prediction], positive: str, exclude_gray: bool = False) -> QMetrics:
    rows = [p for p in preds if p.question == qid and p.gold is not None]
    n_err = sum(1 for p in rows if p.error)
    ok = [p for p in rows if not p.error and not (exclude_gray and p.gray)]
    if not ok:
        return QMetrics(question=qid, n=0, n_pos=0, n_errors=n_err)
    y = np.array([1 if p.gold == positive else 0 for p in ok])
    yhat = np.array([1 if p.label == positive else 0 for p in ok])
    pp = np.array([p.p_positive for p in ok])
    tp = int(((y == 1) & (yhat == 1)).sum()); fp = int(((y == 0) & (yhat == 1)).sum())
    fn = int(((y == 1) & (yhat == 0)).sum()); tn = int(((y == 0) & (yhat == 0)).sum())
    m = QMetrics(question=qid, n=len(ok), n_pos=int(y.sum()), n_errors=n_err, tp=tp, fp=fp, fn=fn, tn=tn)
    m.accuracy = float((y == yhat).mean())
    m.precision = float(precision_score(y, yhat, zero_division=0))
    m.recall = float(recall_score(y, yhat, zero_division=0))
    m.recall_ci = wilson(tp, tp + fn)
    m.f1 = float(f1_score(y, yhat, zero_division=0))
    m.specificity = tn / (tn + fp) if (tn + fp) else None
    m.elusion = fn / (fn + tn) if (fn + tn) else None
    m.kappa = float(cohen_kappa_score(y, yhat)) if len(set(y)) > 1 and len(set(yhat)) > 1 else None
    if len(set(y)) > 1:
        m.roc_auc = float(roc_auc_score(y, pp))
        m.pr_auc = float(average_precision_score(y, pp))
        m.log_loss = float(log_loss(y, np.clip(pp, 1e-6, 1 - 1e-6)))
        m.best_f1, m.best_f1_threshold = best_f1(y, pp)
    m.brier = float(brier_score_loss(y, pp))
    m.ece = ece_score(y, pp)
    m.recall_targets = recall_targets(y, pp)
    return m


def pooled_metrics(preds: list[Prediction], positive: str, exclude_gray: bool = False) -> QMetrics:
    """Micro-pooled over all (doc, question) decisions."""
    qids = sorted({p.question for p in preds})
    tagged = [Prediction(**{**p.to_row(), "question": "__all__"}) for p in preds]
    m = question_metrics("__all__", tagged, positive, exclude_gray)
    m.question = f"pooled({len(qids)} q)"
    return m


def macro_f1(qms: list[QMetrics]) -> float | None:
    vals = [q.f1 for q in qms if q.f1 is not None and q.n_pos > 0]
    return float(np.mean(vals)) if vals else None


def op_metrics(preds: list[Prediction]) -> OpMetrics:
    ok = [p for p in preds if not p.error]
    lat = [p.latency_ms for p in ok if p.latency_ms is not None]
    modes: dict[str, int] = {}
    for p in ok:
        modes[p.pricing_mode] = modes.get(p.pricing_mode, 0) + 1
    n = max(1, len(ok))
    return OpMetrics(
        latency_p50_ms=float(np.percentile(lat, 50)) if lat else None,
        latency_p95_ms=float(np.percentile(lat, 95)) if lat else None,
        input_tokens_mean=float(np.mean([p.input_tokens for p in ok])) if ok else 0.0,
        output_tokens_mean=float(np.mean([p.output_tokens for p in ok])) if ok else 0.0,
        cached_tokens_mean=float(np.mean([p.cached_tokens for p in ok])) if ok else 0.0,
        total_cost_usd=float(sum(p.cost_usd for p in ok)),
        total_list_cost_usd=float(sum(p.list_cost_usd for p in ok)),
        cost_per_1k_docs_usd=float(sum(p.list_cost_usd for p in ok)) / n * 1000,
        pricing_modes=modes,
    )


def agreement(a: list[Prediction], b: list[Prediction]) -> float | None:
    la = {(p.doc_id, p.question): p.label for p in a if not p.error}
    lb = {(p.doc_id, p.question): p.label for p in b if not p.error}
    common = sorted(set(la) & set(lb))
    if len(common) < 2:
        return None
    x = [la[k] for k in common]; y = [lb[k] for k in common]
    if x == y:
        return 1.0
    return float(cohen_kappa_score(x, y))

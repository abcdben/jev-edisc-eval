"""Classification, calibration, and operational metrics.

Binary tasks get the full eDiscovery set (precision, recall, F1, elusion, AUCs,
calibration, recall-at-precision thresholds). Multiclass tasks get accuracy,
macro-F1, and kappa. All tasks get latency and cost.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

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
from .tasks import Task


@dataclass
class Summary:
    model: str
    model_resolved: str
    n: int
    n_errors: int
    # classification (argmax / provider label)
    accuracy: float
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    specificity: float | None = None
    elusion: float | None = None  # FN / (FN + TN): responsive docs hiding in the "not" pile
    kappa: float | None = None
    macro_f1: float | None = None
    tp: int | None = None
    fp: int | None = None
    fn: int | None = None
    tn: int | None = None
    # ranking / probability quality (binary)
    roc_auc: float | None = None
    pr_auc: float | None = None
    brier: float | None = None
    log_loss: float | None = None
    ece: float | None = None
    # threshold analysis (binary): what threshold on p(positive) hits a recall target,
    # and what precision you get there. This is the TAR-style view.
    recall_targets: dict[str, dict[str, float]] = field(default_factory=dict)
    # operational
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_mean_ms: float = 0.0
    input_tokens_mean: float = 0.0
    output_tokens_mean: float = 0.0
    total_cost_usd: float = 0.0
    cost_per_1k_docs_usd: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p > lo) & (p <= hi) if lo > 0 else (p >= lo) & (p <= hi)
        if m.sum() == 0:
            continue
        ece += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(ece)


def _recall_targets(y: np.ndarray, p: np.ndarray, targets=(0.75, 0.80, 0.90, 0.95)) -> dict:
    """For each recall target, the highest threshold achieving it and metrics there."""
    out = {}
    order = np.argsort(-p)
    ps, ys = p[order], y[order]
    n_pos = ys.sum()
    if n_pos == 0:
        return out
    cum_tp = np.cumsum(ys)
    for t in targets:
        idx = np.argmax(cum_tp >= t * n_pos)  # first index where recall >= t
        if cum_tp[idx] < t * n_pos:
            continue
        k = idx + 1
        thr = float(ps[idx])
        prec = float(cum_tp[idx] / k)
        rec = float(cum_tp[idx] / n_pos)
        out[f"recall@{int(t*100)}"] = {
            "threshold": thr,
            "precision": prec,
            "recall": rec,
            "review_fraction": float(k / len(y)),  # share of corpus you'd have to review
        }
    return out


def summarize(task: Task, preds: list[Prediction]) -> Summary:
    ok = [p for p in preds if not p.error and p.gold is not None]
    n_err = sum(1 for p in preds if p.error)
    resolved = next((p.model_resolved for p in ok), preds[0].model_resolved if preds else "")

    if not ok:
        return Summary(model=preds[0].model_key if preds else "?", model_resolved=resolved, n=0, n_errors=n_err, accuracy=float("nan"))

    gold = np.array([p.gold for p in ok])
    pred = np.array([p.label for p in ok])
    s = Summary(
        model=ok[0].model_key,
        model_resolved=resolved,
        n=len(ok),
        n_errors=n_err,
        accuracy=float((gold == pred).mean()),
    )

    lat = np.array([p.latency_ms for p in ok])
    s.latency_p50_ms = float(np.percentile(lat, 50))
    s.latency_p95_ms = float(np.percentile(lat, 95))
    s.latency_mean_ms = float(lat.mean())
    s.input_tokens_mean = float(np.mean([p.input_tokens for p in ok]))
    s.output_tokens_mean = float(np.mean([p.output_tokens for p in ok]))
    s.total_cost_usd = float(sum(p.cost_usd for p in ok))
    s.cost_per_1k_docs_usd = s.total_cost_usd / len(ok) * 1000

    if task.kind == "binary":
        pos = task.positive_label
        y = (gold == pos).astype(int)
        yhat = (pred == pos).astype(int)
        p = np.array([pr.probabilities.get(pos, 0.0) for pr in ok])

        tp = int(((y == 1) & (yhat == 1)).sum())
        fp = int(((y == 0) & (yhat == 1)).sum())
        fn = int(((y == 1) & (yhat == 0)).sum())
        tn = int(((y == 0) & (yhat == 0)).sum())
        s.tp, s.fp, s.fn, s.tn = tp, fp, fn, tn
        s.precision = float(precision_score(y, yhat, zero_division=0))
        s.recall = float(recall_score(y, yhat, zero_division=0))
        s.f1 = float(f1_score(y, yhat, zero_division=0))
        s.specificity = tn / (tn + fp) if (tn + fp) else None
        s.elusion = fn / (fn + tn) if (fn + tn) else None
        s.kappa = float(cohen_kappa_score(y, yhat)) if len(set(y)) > 1 else None

        if len(set(y)) > 1:
            s.roc_auc = float(roc_auc_score(y, p))
            s.pr_auc = float(average_precision_score(y, p))
            s.log_loss = float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6)))
        s.brier = float(brier_score_loss(y, p))
        s.ece = expected_calibration_error(y, p)
        s.recall_targets = _recall_targets(y, p)
    else:
        labels = task.label_names
        s.macro_f1 = float(f1_score(gold, pred, labels=labels, average="macro", zero_division=0))
        s.kappa = float(cohen_kappa_score(gold, pred)) if len(set(gold)) > 1 else None
        # Multiclass probability quality: Brier over one-hot, ECE on max-prob
        onehot = np.array([[1.0 if g == l else 0.0 for l in labels] for g in gold])
        P = np.array([[pr.probabilities.get(l, 0.0) for l in labels] for pr in ok])
        s.brier = float(((P - onehot) ** 2).sum(axis=1).mean())
        conf = P.max(axis=1)
        s.ece = expected_calibration_error((gold == pred).astype(int), conf)

    return s


def agreement_matrix(task: Task, results: dict[str, list[Prediction]]) -> dict[str, dict[str, float]]:
    """Pairwise Cohen's kappa between models (how often they agree with each other)."""
    keys = list(results)
    by_model = {k: {p.doc_id: p.label for p in results[k] if not p.error} for k in keys}
    out: dict[str, dict[str, float]] = {}
    for a in keys:
        out[a] = {}
        for b in keys:
            common = sorted(set(by_model[a]) & set(by_model[b]))
            if len(common) < 2:
                out[a][b] = float("nan")
                continue
            la = [by_model[a][d] for d in common]
            lb = [by_model[b][d] for d in common]
            out[a][b] = 1.0 if la == lb else float(cohen_kappa_score(la, lb))
    return out

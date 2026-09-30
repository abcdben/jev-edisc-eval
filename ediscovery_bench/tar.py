"""Classical TAR baselines: a human reviewer plus a TF-IDF / logistic-regression classifier.

Two workflows, both simulated against the gold labels (the "reviewer" codes a document by reading its
gold labels, optionally with a miscoding rate):

  TAR 1.0  (simple learning)   The reviewer codes a random training sample of N documents. One
           classifier per issue plus one for "responsive to any issue" is trained on it. A cutoff is
           chosen by 5-fold cross-validation on the training sample alone (no peeking at the rest),
           either targeting 80% recall or maximising F1. Output over the whole corpus = the reviewer's
           codes on the N training documents + the classifier's calls on the remainder.
           The `_div` variants replace the random draw with cluster-stratified diversity sampling: the
           pool's TF-IDF matrix is reduced with a 100-dimension truncated SVD (fit on at most 50k
           candidates, all candidates projected, rows L2-normalised), MiniBatchKMeans finds N clusters,
           and the candidate nearest each centroid is coded (empty clusters are filled at random). The
           cutoff is still chosen by CV on the coded sample for comparability, but that sample is no
           longer random, so its recall estimate is only a guide.

  TAR 2.0  (continuous active learning)   Before learning starts the reviewer codes a simple random
           control set drawn from the pool (10% of the pool, capped at 500, and at least enough for ~30
           relevant documents; a fixed 2,000 on TREC's 286k collection). Control documents never enter the
           review queue and are not trained on; their coding counts as review effort and their codes are
           part of the production set. Seed = random documents + the highest keyword-floor scores. Loop:
           train on everything queued and coded, rank the pool, the reviewer codes the top batch, repeat.
           The control documents ride along virtually: whenever a batch is picked, every control document
           scoring at or above the batch's lowest queued score counts as reached from then on, and recall
           is estimated as the share of control-set documents the reviewer coded relevant that have been
           reached. Stop when the estimate is at or above the target (80%; `cal_75` uses 75%) for two
           consecutive batches, or when the pool is exhausted.
           The `cal_knee` variant stops by the knee method instead (Cormack & Grossman 2016: pre-knee slope
           >= 6x post-knee, after 10% of the collection) and draws no control set.
           What the site plots is the production set: every document the (imperfect, by default) reviewer
           coded relevant, control set included, scored against gold on the pool CAL ran over. The sidecar
           also records review-set precision, the recall estimate at stop against the true figure, and
           the final classifier applied on its own to the evaluation set at the control-set cutoff.
           Mallinckrodt's benchmark sample is 61% rich by design; CAL there runs on a 10%-rich pool (all
           gold-negative emails plus a per-seed random draw of positives).

Reviewer economics: 50 documents/hour, $65/hour. Compute is negligible and not charged.

Layout mirrors the API runs so export.py can pick the rows up:
  results/<corpus>/multi/tar__<variant>.jsonl        Prediction rows for the median seed (by doc-level F1)
  results/<corpus>/multi/tar__<variant>.tar.json     sidecar: review effort, cutoffs, spread across seeds
  results/trec_full/multi/tar__<variant>.jsonl       TREC: positive rows only over the 286k collection

Variants: t1_<N> (80%-recall cutoff, perfect reviewer), t1_<N>_f1 (F1 cutoff), t1_<N>_noisy (imperfect
reviewer: misses 10% of relevant, over-codes 2% of non-relevant), t1_<N>_div (diversity-sampled training
set, otherwise as t1_<N>), t1_<N>_acc<60|70|80|90> and their `_div` counterparts (reviewer sensitivity
sweep; false-positive rate is one-fifth of the miss rate), cal (imperfect reviewer, 80% target),
cal_75 (75% target), cal_perfect (perfect reviewer, 80% target), cal_knee (imperfect reviewer, knee stop).
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import numpy as np
from rich.console import Console
from scipy import sparse
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import normalize

from .providers.base import Prediction
from .tasks import Document, TaskSet, load_corpus

console = Console(width=200)

DOCS_PER_HOUR = 50.0
USD_PER_HOUR = 65.0
SEEDS = 5
MIN_POS_FOR_ISSUE_MODEL = 5
CAL_TARGET = 0.80  # recall target for the control-set stopping rule
CAL_PATIENCE = 2  # consecutive batches at or above the target before stopping
CONTROL_SHARE = 0.10  # control set: this share of the pool ...
CONTROL_CAP = 500  # ... capped here ...
CONTROL_MIN_RELEVANT = 30  # ... but at least enough documents to expect this many relevant ones
KNEE_SLOPE_RATIO = 6.0
KNEE_MIN_EFFORT = 0.10
CAL_RICHNESS_CAP = 0.15  # pools richer than this are downsampled to CAL_TARGET_RICHNESS for the CAL rows
CAL_TARGET_RICHNESS = 0.10
NOISE_RATE = 0.10  # imperfect reviewer: misses 10% of relevant documents ...
NOISE_FP_RATIO = 0.2  # ... and over-codes 2% of non-relevant ones
REVIEWER_ACCURACIES = (60, 70, 80, 90)
DIV_SVD_DIMS = 100  # diversity sampling: TF-IDF -> truncated SVD with this many dimensions ...
DIV_SVD_FIT_CAP = 50_000  # ... fit on at most this many candidates (all candidates are projected)

# corpus key -> (task yaml, evaluation corpus, training/CAL pool, keyword-floor results, cal batch, cal seeds,
#                control-set size: None = CONTROL_SHARE / CONTROL_CAP / CONTROL_MIN_RELEVANT rule, else fixed)
CORPORA = {
    "mnk": dict(task="tasks/mallinckrodt.yaml", eval="data/mallinckrodt/mnk.jsonl", pool=None, lexical="results/mnk/multi/lexical.jsonl", batch=50, seed_n=50, cal_seeds=SEEDS, stages=[100, 300, 1000], control=None),
    "cuad": dict(task="tasks/cuad.yaml", eval="data/cuad/cuad.jsonl", pool=None, lexical="results/cuad/multi/lexical.jsonl", batch=100, seed_n=100, cal_seeds=SEEDS, stages=[100, 1000, 5000], control=None),
    "trec": dict(task="tasks/trec.yaml", eval="data/trec/eval.jsonl", pool="data/trec/full.jsonl", lexical="results/trec_full/multi/lexical.jsonl", batch=1000, seed_n=100, cal_seeds=3, stages=[100, 1000, 5000, 7500, 10000], control=2000),
}


# ------------------------------------------------------------------------------------------------ reviewer

class Reviewer:
    """Codes a document from its gold labels. The imperfect reviewer misses a share of relevant documents
    (coded not relevant on every issue) and over-codes a smaller share of non-relevant ones (coded relevant
    on one issue chosen at random); `noise` is the miss rate and the over-code rate is NOISE_FP_RATIO of
    it. The miscode is fixed per document so training and output agree."""

    def __init__(self, ts: TaskSet, docs: dict[str, Document], noise: float, seed: int):
        self.ts, self.docs, self.noise = ts, docs, noise
        self.rng = np.random.default_rng(seed * 7919 + 17)
        self.codes: dict[str, dict[str, bool]] = {}
        self.n_reviewed = 0

    def gold(self, doc_id: str) -> dict[str, bool]:
        d = self.docs[doc_id]
        return {q: d.labels.get(q) == self.ts.positive_label for q in self.ts.qids}

    def code(self, doc_id: str) -> dict[str, bool]:
        if doc_id in self.codes:
            return self.codes[doc_id]
        g = self.gold(doc_id)
        if self.noise:
            u = self.rng.random()
            if any(g.values()) and u < self.noise:
                g = {q: False for q in g}
            elif not any(g.values()) and u < self.noise * NOISE_FP_RATIO:
                q = self.ts.qids[int(self.rng.integers(len(self.ts.qids)))]
                g = {k: k == q for k in g}
        self.codes[doc_id] = g
        self.n_reviewed += 1
        return g

    @property
    def hours(self) -> float:
        return self.n_reviewed / DOCS_PER_HOUR

    @property
    def cost(self) -> float:
        return self.hours * USD_PER_HOUR


# ------------------------------------------------------------------------------------------------ features

def featurize(texts: list[str]) -> sparse.csr_matrix:
    """TF-IDF over word 1-2 grams. Above ~50k documents the bigram vocabulary no longer fits in memory, so
    the terms are hashed into 2^20 buckets instead (same model family, bounded memory)."""
    if len(texts) <= 50_000:
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=300_000, sublinear_tf=True, dtype=np.float32, strip_accents="unicode")
        return vec.fit_transform(texts)
    hv = HashingVectorizer(ngram_range=(1, 2), n_features=2**20, alternate_sign=False, norm=None, dtype=np.float32, strip_accents="unicode")
    X = hv.transform(texts)
    return TfidfTransformer(sublinear_tf=True).fit_transform(X).astype(np.float32).tocsr()


def fit(X, y: np.ndarray) -> LogisticRegression | None:
    if y.sum() == 0 or y.sum() == len(y):
        return None
    clf = LogisticRegression(solver="liblinear", class_weight="balanced", C=1.0, max_iter=1000)
    clf.fit(X, y)
    return clf


def scores(clf: LogisticRegression | None, X) -> np.ndarray:
    if clf is None:
        return np.full(X.shape[0], -10.0, dtype=np.float32)
    return clf.decision_function(X).astype(np.float32)


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def cv_scores(X, y: np.ndarray, seed: int) -> np.ndarray | None:
    """Out-of-fold decision scores on the training sample; None when too few positives to fold."""
    npos = int(y.sum())
    k = min(5, npos, len(y) - npos)
    if k < 2:
        return None
    oof = np.zeros(len(y), dtype=np.float32)
    for tr, te in StratifiedKFold(n_splits=k, shuffle=True, random_state=seed).split(X, y):
        clf = fit(X[tr], y[tr])
        oof[te] = scores(clf, X[te])
    return oof


def cutoff(oof: np.ndarray | None, y: np.ndarray, rule: str) -> float:
    """Decision-function threshold from out-of-fold scores. recall80: the largest threshold keeping
    OOF recall >= 0.8. f1: the threshold maximising OOF F1. Falls back to 0 (p = 0.5) when unfoldable."""
    if oof is None:
        return 0.0
    pos = np.sort(oof[y == 1])[::-1]
    if rule == "recall80":
        k = int(math.ceil(0.8 * len(pos))) - 1
        return float(pos[max(0, k)]) - 1e-6
    order = np.argsort(-oof)
    ys = y[order]
    tp = np.cumsum(ys); fp = np.cumsum(1 - ys); fn = ys.sum() - tp
    f1 = 2 * tp / np.maximum(1, 2 * tp + fp + fn)
    i = int(np.argmax(f1))
    return float(oof[order][i]) - 1e-6


# ------------------------------------------------------------------------------------------------ rows

def _row(doc_id: str, q: str, model_key: str, label: bool, p: float, resolved: str, raw: dict | None = None) -> Prediction:
    return Prediction(doc_id=doc_id, question=q, model_key=model_key, model_resolved=resolved, arm="multi",
                      label="responsive" if label else "not_responsive", p_positive=float(min(0.999, max(0.001, p))),
                      confidence=None, latency_ms=0.0, input_tokens=0, output_tokens=0, cached_tokens=0,
                      cost_usd=0.0, list_cost_usd=0.0, pricing_mode="simulated reviewer", raw=raw or {})


def doc_level(rows_by_doc: dict[str, dict[str, bool]], gold: dict[str, dict[str, bool]]) -> dict:
    tp = fp = fn = 0
    for d, g in gold.items():
        pr = any(rows_by_doc.get(d, {}).values()); gp = any(g.values())
        tp += pr and gp; fp += pr and not gp; fn += (not pr) and gp
    r = tp / (tp + fn) if tp + fn else None
    p = tp / (tp + fp) if tp + fp else None
    f1 = 2 * p * r / (p + r) if p and r else 0.0
    return {"recall": r, "precision": p, "f1": f1, "flagged": tp + fp, "relevant": tp + fn}


# ------------------------------------------------------------------------------------------------ TAR 1.0

_DIV_EMBED_CACHE: dict[tuple[int, int], np.ndarray] = {}  # (id(X), seed) -> SVD embedding of the candidates
_DIV_SAMPLE_CACHE: dict[tuple[int, int, int], tuple[np.ndarray, dict]] = {}  # (id(X), seed, n) -> picks/meta


def _div_embedding(X, cand: np.ndarray, seed: int) -> np.ndarray:
    """L2-normalised DIV_SVD_DIMS-dimensional truncated-SVD embedding of the candidate rows of X. The SVD is
    fit on at most DIV_SVD_FIT_CAP candidates (a seeded draw) and every candidate is projected. Cached per
    (matrix, seed) so the sample sizes of one seed share the embedding."""
    key = (id(X), seed)
    if key in _DIV_EMBED_CACHE:
        return _DIV_EMBED_CACHE[key]
    rng = np.random.default_rng(seed * 104_729 + 7)
    Xc = X[cand]
    fit_rows = rng.choice(len(cand), size=DIV_SVD_FIT_CAP, replace=False) if len(cand) > DIV_SVD_FIT_CAP else None
    svd = TruncatedSVD(n_components=min(DIV_SVD_DIMS, Xc.shape[1] - 1), algorithm="randomized", random_state=seed)
    svd.fit(Xc if fit_rows is None else Xc[fit_rows])
    Z = normalize(svd.transform(Xc)).astype(np.float32)
    _DIV_EMBED_CACHE[key] = Z  # 286k x 100 float32 per seed on TREC: ~115 MB each
    return Z


def diversity_sample(X, cand: np.ndarray, n: int, seed: int) -> tuple[np.ndarray, dict]:
    """Cluster-stratified diversity sample of `n` candidates: k-means with k = n on the SVD embedding, then the
    candidate nearest each centroid (one per cluster, so the picks are distinct). Clusters that end up empty
    contribute nothing and the shortfall is filled by a seeded random draw from the rest. Returns the chosen
    pool indices and a meta block."""
    n = min(n, len(cand))
    key = (id(X), seed, n)
    if key in _DIV_SAMPLE_CACHE:
        picks, meta = _DIV_SAMPLE_CACHE[key]
        return picks.copy(), dict(meta)
    Z = _div_embedding(X, cand, seed)
    km = MiniBatchKMeans(n_clusters=n, random_state=seed, batch_size=4096, n_init=1, max_iter=100, init_size=max(3 * n, 10_000))
    labels = km.fit_predict(Z)
    picks: list[int] = []
    for c in range(n):
        members = np.flatnonzero(labels == c)
        if len(members) == 0:
            continue
        d = ((Z[members] - km.cluster_centers_[c].astype(np.float32)) ** 2).sum(axis=1)
        picks.append(int(members[int(np.argmin(d))]))
    empty = n - len(picks)
    if empty:
        rng = np.random.default_rng(seed)
        rest = np.setdiff1d(np.arange(len(cand)), np.array(picks, dtype=int))
        picks += [int(i) for i in rng.choice(rest, size=empty, replace=False)]
    meta = {"sampling": "diversity", "svd_dims": int(Z.shape[1]), "svd_fit_rows": int(min(len(cand), DIV_SVD_FIT_CAP)), "k": n,
            "empty_clusters": int(empty), "kmeans": "MiniBatchKMeans, one document nearest each centroid"}
    selected = cand[np.array(picks, dtype=int)]
    _DIV_SAMPLE_CACHE[key] = (selected.copy(), dict(meta))
    return selected, meta


def run_tar1(ts: TaskSet, pool: list[Document], pool_idx: dict[str, int], X, eval_docs: list[Document],
             eval_idx: np.ndarray, n_train: int, rule: str, noise: float, seed: int, exclude: set[str],
             sampling: str = "random") -> tuple[dict[str, dict[str, bool]], dict[str, np.ndarray], dict]:
    """Returns (decisions on eval docs keyed by id, per-issue probabilities on eval docs, run meta).
    `sampling` is "random" (simple random sample of the candidates) or "diversity" (see diversity_sample)."""
    rng = np.random.default_rng(seed)
    cand = np.array([i for i, d in enumerate(pool) if d.id not in exclude])
    if sampling == "diversity":
        t_s = time.time()
        train, sample_meta = diversity_sample(X, cand, n_train, seed)
        sample_meta["sample_seconds"] = round(time.time() - t_s, 1)
    else:
        train = rng.choice(cand, size=min(n_train, len(cand)), replace=False)
        sample_meta = {"sampling": "random"}
    rev = Reviewer(ts, {d.id: d for d in pool}, noise, seed)
    codes = [rev.code(pool[i].id) for i in train]
    Xtr = X[train]
    y_any = np.array([any(c.values()) for c in codes], dtype=int)
    clf_any = fit(Xtr, y_any)
    t_any = cutoff(cv_scores(Xtr, y_any, seed), y_any, rule)
    issue_models: dict[str, tuple[LogisticRegression, float]] = {}
    pos_counts = {q: int(sum(c[q] for c in codes)) for q in ts.qids}
    for q in ts.qids:
        yq = np.array([c[q] for c in codes], dtype=int)
        if yq.sum() >= MIN_POS_FOR_ISSUE_MODEL and yq.sum() < len(yq):
            m = fit(Xtr, yq)
            if m is not None:
                issue_models[q] = (m, cutoff(cv_scores(Xtr, yq, seed), yq, rule))
    fallback_issue = max(ts.qids, key=lambda q: pos_counts[q])  # what the reviewer tagged most often

    Xev = X[eval_idx]
    s_any = scores(clf_any, Xev)
    s_issue = {q: scores(m, Xev) for q, (m, _) in issue_models.items()}
    trained_ids = {pool[i].id for i in train}
    decisions: dict[str, dict[str, bool]] = {}
    probs: dict[str, np.ndarray] = {q: np.zeros(len(eval_docs), dtype=np.float32) for q in ts.qids}
    for j, d in enumerate(eval_docs):
        if d.id in trained_ids:
            c = rev.code(d.id)
            decisions[d.id] = dict(c)
            for q in ts.qids:
                probs[q][j] = 1.0 if c[q] else 0.0
            continue
        flagged = bool(s_any[j] >= t_any)
        dec = {}
        for q in ts.qids:
            if q in issue_models:
                dec[q] = flagged and bool(s_issue[q][j] >= issue_models[q][1])
                probs[q][j] = sigmoid(np.array([s_issue[q][j]]))[0]
            else:
                dec[q] = False
                probs[q][j] = sigmoid(np.array([s_any[j]]))[0] * 0.5
        if flagged and not any(dec.values()):
            if issue_models:
                best = max(issue_models, key=lambda q: s_issue[q][j] - issue_models[q][1])
            else:
                best = fallback_issue
            dec[best] = True
        decisions[d.id] = dec
    meta = {"n_train": int(len(train)), "rule": rule, "noise": noise, "seed": seed, "cutoff_any": round(t_any, 4),
            "issue_models": sorted(issue_models), "train_positives_any": int(y_any.sum()), "train_positives_by_issue": pos_counts,
            "hours": rev.hours, "cost_usd": rev.cost, "docs_reviewed": rev.n_reviewed, **sample_meta}
    return decisions, probs, meta


# ------------------------------------------------------------------------------------------------ TAR 2.0 / CAL

def knee_stop(curve: list[dict], n_pool: int) -> bool:
    """Cormack & Grossman's knee method on the gain curve (found vs reviewed): locate the knee as the point
    farthest from the chord joining the origin to the current point; stop when the slope up to the knee is
    at least KNEE_SLOPE_RATIO times the slope after it, once KNEE_MIN_EFFORT of the collection is reviewed."""
    if len(curve) < 3 or curve[-1]["reviewed"] < KNEE_MIN_EFFORT * n_pool:
        return False
    xs = np.array([0] + [c["reviewed"] for c in curve], dtype=float); ys = np.array([0] + [c["found"] for c in curve], dtype=float)
    x1, y1 = xs[-1], ys[-1]
    if x1 == 0 or y1 == 0:
        return False
    dist = np.abs(y1 * xs - x1 * ys) / math.hypot(x1, y1)
    k = int(np.argmax(dist[:-1]))
    if xs[k] == 0 or xs[-1] == xs[k]:
        return False
    before = ys[k] / xs[k]
    after = (ys[-1] - ys[k] + 1) / (xs[-1] - xs[k])  # +1: one undiscovered relevant document, as in the paper
    return before / after >= KNEE_SLOPE_RATIO


def cal_pool(ts: TaskSet, docs: list[Document], seed: int) -> list[int]:
    """Indices of the documents CAL runs over. Collections richer than CAL_RICHNESS_CAP are downsampled to
    CAL_TARGET_RICHNESS by keeping every gold-negative document and a random draw of the positives."""
    pos_ids = [i for i, d in enumerate(docs) if any(d.labels.get(q) == ts.positive_label for q in ts.qids)]
    neg_ids = [i for i in range(len(docs)) if i not in set(pos_ids)]
    if len(pos_ids) / len(docs) <= CAL_RICHNESS_CAP:
        return list(range(len(docs)))
    k = int(round(len(neg_ids) * CAL_TARGET_RICHNESS / (1 - CAL_TARGET_RICHNESS)))
    rng = np.random.default_rng(1_000_003 + seed)
    keep = sorted(neg_ids + list(rng.choice(pos_ids, size=k, replace=False)))
    return keep


def control_size(n: int, richness: float, fixed: int | None) -> int:
    """Control-set size: CONTROL_SHARE of the pool, capped at CONTROL_CAP, but at least enough documents to
    expect CONTROL_MIN_RELEVANT relevant ones at the pool's richness (never more than half the pool)."""
    if fixed is not None:
        return min(fixed, n)
    want = max(CONTROL_SHARE * n, CONTROL_MIN_RELEVANT / max(richness, 1e-6))
    return int(min(CONTROL_CAP, want, n // 2))


def _prf(flag: np.ndarray, gold: np.ndarray) -> dict:
    tp = int((flag & gold).sum()); fp = int((flag & ~gold).sum()); fn = int((~flag & gold).sum())
    return {"recall": tp / (tp + fn) if tp + fn else None, "precision": tp / (tp + fp) if tp + fp else None,
            "flagged": tp + fp, "relevant": tp + fn, "n": int(len(flag))}


def run_cal(ts: TaskSet, pool: list[Document], X, kw_score: np.ndarray, batch: int, seed_n: int, noise: float, seed: int,
            stop: str, target: float | None, control_n: int | None, X_eval, gold_eval: np.ndarray, eval_ids: list[str]) -> tuple[Reviewer, np.ndarray, dict]:
    """Continuous active learning over the pool. Returns the reviewer (its codes are the production set),
    the final relevance scores over the pool, and run meta.

    stop = "target": a random control set of `control_n` documents is coded first (effort counted, never
    queued, never trained on). The control documents ride along in the queue virtually: whenever the model
    picks a batch, every control document scoring at or above that batch's lowest queued score counts as
    reached from then on (it would have been in the batch had it not been held out), and likewise for the
    keyword seed. Recall is estimated as the share of the control documents the reviewer coded relevant
    that have been reached. Stop once the estimate is >= `target` for CAL_PATIENCE consecutive batches.
    (Ranking the pool with the *current* model and counting control documents above the review depth is
    biased low once the training positives crowd the top of the ranking; the virtual queue mirrors what
    actually happened to the reviewed documents.) stop = "knee": Cormack & Grossman's knee method, no
    control set.

    At stop the final classifier is also applied on its own, at the score that reaches `target` recall on
    the control set, to the pool and to the evaluation set (X_eval / gold_eval), for a like-for-like view
    of the classifier's quality without the reviewer."""
    rng = np.random.default_rng(seed)
    n = len(pool)
    gold_any = np.array([any(d.labels.get(q) == ts.positive_label for q in ts.qids) for d in pool])
    rev = Reviewer(ts, {d.id: d for d in pool}, noise, seed)
    coded = np.zeros(n, dtype=bool)  # queued and coded: the training set
    ctrl = np.zeros(n, dtype=bool)
    ctrl_rel_idx = np.zeros(0, dtype=int)
    if stop == "target" and control_n:
        ctrl_idx = rng.choice(n, size=min(control_n, n), replace=False)
        ctrl[ctrl_idx] = True
        ctrl_rel_idx = np.array([i for i in ctrl_idx if any(rev.code(pool[i].id).values())], dtype=int)
    ctrl_reached = np.zeros(n, dtype=bool)  # control documents that would have been queued by now
    avail = np.flatnonzero(~ctrl)
    seed_idx = [int(i) for i in rng.choice(avail, size=min(seed_n, len(avail)), replace=False)]
    kw_floor = None
    for i in np.argsort(-kw_score):
        if len(seed_idx) >= 2 * seed_n:
            break
        if not ctrl[i] and i not in seed_idx:
            seed_idx.append(int(i)); kw_floor = kw_score[i]
    if kw_floor is not None and kw_floor > 0:
        ctrl_reached |= ctrl & (kw_score >= kw_floor)
    y = np.zeros(n, dtype=int)
    for i in seed_idx:
        c = rev.code(pool[i].id); coded[i] = True; y[i] = any(c.values())
    # a seed with no positives cannot train: keep drawing random batches (what a team would do)
    while y[coded].sum() == 0 and (coded | ctrl).sum() < n:
        rest = np.flatnonzero(~(coded | ctrl))
        for i in rng.choice(rest, size=min(batch, len(rest)), replace=False):
            c = rev.code(pool[i].id); coded[i] = True; y[i] = any(c.values())

    def est_recall() -> float | None:
        """Share of reviewer-relevant control documents that would have been queued by now."""
        return float(ctrl_reached[ctrl_rel_idx].mean()) if len(ctrl_rel_idx) else None

    curve = [{"reviewed": int(coded.sum()), "found": int(y[coded].sum()), "found_gold": int(gold_any[coded].sum()), "est_recall": None}]
    why = "pool exhausted"
    streak = 0
    est: float | None = None
    s_raw = np.full(n, -10.0, dtype=np.float32)
    t0 = time.time()
    while True:
        clf = fit(X[coded], y[coded])
        s_raw = scores(clf, X)
        if stop == "target":
            est = est_recall()
            curve[-1]["est_recall"] = None if est is None else round(est, 4)
            streak = streak + 1 if est is not None and target is not None and est >= target else 0
            if streak >= CAL_PATIENCE:
                why = f"control-set recall estimate ≥ {target:.0%} for {CAL_PATIENCE} consecutive batches"; break
        elif knee_stop(curve, n):
            why = f"knee method: pre-knee slope ≥ {KNEE_SLOPE_RATIO:g}× post-knee slope, after ≥ {KNEE_MIN_EFFORT:.0%} of the collection"; break
        if (coded | ctrl).sum() >= n:
            break
        s_rank = s_raw.copy(); s_rank[coded | ctrl] = -np.inf
        take = np.argsort(-s_rank)[: min(batch, int((~(coded | ctrl)).sum()))]
        ctrl_reached |= ctrl & (s_raw >= s_raw[take].min())
        for i in take:
            c = rev.code(pool[i].id); coded[i] = True; y[i] = any(c.values())
        curve.append({"reviewed": int(coded.sum()), "found": int(y[coded].sum()), "found_gold": int(gold_any[coded].sum()), "est_recall": None})

    # production set (what the reviewer coded relevant) and review set (everything read), against gold on the pool
    produced = np.array([any(rev.codes[d.id].values()) if d.id in rev.codes else False for d in pool])
    reviewed = coded | ctrl
    production = _prf(produced, gold_any)
    review_set = {"n": int(reviewed.sum()), "precision": float(gold_any[reviewed].mean()) if reviewed.any() else None,
                  "recall": float(gold_any[reviewed].sum() / max(1, gold_any.sum()))}
    # the classifier on its own, cut at the score that reaches the target on the control set
    classifier = None
    if len(ctrl_rel_idx) and target is not None:
        pos = np.sort(s_raw[ctrl_rel_idx])[::-1]
        tau_star = float(pos[max(0, int(math.ceil(target * len(pos))) - 1)])
        s_eval = scores(clf, X_eval)
        n_eval_reviewed = int(sum(1 for d in eval_ids if d in rev.codes))
        classifier = {"cutoff": round(tau_star, 4), "target": target,
                      "pool": _prf(s_raw >= tau_star, gold_any),
                      "eval": {**_prf(s_eval >= tau_star, gold_eval), "n_reviewed_in_eval": n_eval_reviewed}}
    meta = {"noise": noise, "seed": seed, "batch": batch, "seed_docs": len(seed_idx), "docs_reviewed": rev.n_reviewed,
            "docs_queued": int(coded.sum()), "hours": rev.hours, "cost_usd": rev.cost, "batches": len(curve) - 1,
            "stop_rule": stop, "target": target, "stop": why,
            "recall_estimator": "control set: a held-out document counts as reached once it would have been queued (its score under the model that picked a batch is at or above the batch's lowest queued score)" if ctrl.any() else None,
            "control_set": {"n": int(ctrl.sum()), "relevant_coded": int(len(ctrl_rel_idx)), "relevant_gold": int(gold_any[ctrl].sum())} if ctrl.any() else None,
            "est_recall_at_stop": None if est is None else round(est, 4),
            "reached_recall": review_set["recall"], "review_set_precision": review_set["precision"],
            "production": production, "classifier": classifier, "plotted": "production set on pool",
            "found_gold": int(gold_any[reviewed].sum()), "relevant_in_pool": int(gold_any.sum()), "pool_richness": float(gold_any.mean()),
            "curve": [curve[i] for i in sorted(set(list(range(0, len(curve), max(1, len(curve) // 60))) + [len(curve) - 1]))],
            "fit_seconds": round(time.time() - t0, 1)}
    return rev, s_raw, meta


# ------------------------------------------------------------------------------------------------ driver

def _keyword_scores(path: Path, ids: list[str]) -> np.ndarray:
    """Max keyword-floor p across issues per document, from the saved lexical run (0 where missing)."""
    idx = {d: i for i, d in enumerate(ids)}
    out = np.zeros(len(ids), dtype=np.float32)
    if not path.exists():
        return out
    with path.open() as f:
        for line in f:
            r = json.loads(line)
            i = idx.get(r["doc_id"])
            if i is not None and r.get("error") is None:
                out[i] = max(out[i], r["p_positive"])
    return out


def _write(rows: list[Prediction], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(asdict(r), separators=(",", ":")) + "\n")


def run_corpus(corpus: str, out: Path = Path("results"), only: str | None = None, seeds: int = SEEDS):
    cfg = CORPORA[corpus]
    ts = TaskSet.load(cfg["task"])
    eval_docs = load_corpus(cfg["eval"])
    pool = load_corpus(cfg["pool"]) if cfg["pool"] else eval_docs
    pool_idx = {d.id: i for i, d in enumerate(pool)}
    eval_idx = np.array([pool_idx[d.id] for d in eval_docs])
    gold_eval = {d.id: {q: d.labels.get(q) == ts.positive_label for q in ts.qids} for d in eval_docs}
    console.print(f"[{corpus}] pool {len(pool):,} docs, eval {len(eval_docs):,}; fitting TF-IDF…")
    t0 = time.time()
    X = featurize([d.text for d in pool])
    _DIV_EMBED_CACHE.clear()
    _DIV_SAMPLE_CACHE.clear()
    console.print(f"[{corpus}] {X.shape[1]:,} features in {time.time() - t0:.0f}s")
    full_out = out / "trec_full" / "multi" if corpus == "trec" else None
    exclude = {d.id for d in eval_docs} if cfg["pool"] else set()

    variants: list[tuple[str, dict]] = []
    for n in cfg["stages"]:
        variants += [(f"t1_{n}", dict(kind="t1", n=n, rule="recall80", noise=0.0, sampling="random")),
                     (f"t1_{n}_f1", dict(kind="t1", n=n, rule="f1", noise=0.0, sampling="random")),
                     (f"t1_{n}_noisy", dict(kind="t1", n=n, rule="recall80", noise=NOISE_RATE, sampling="random")),
                     (f"t1_{n}_div", dict(kind="t1", n=n, rule="recall80", noise=0.0, sampling="diversity"))]
        for accuracy in REVIEWER_ACCURACIES:
            noise = 1.0 - accuracy / 100.0
            variants += [
                (f"t1_{n}_acc{accuracy}", dict(kind="t1", n=n, rule="recall80", noise=noise, sampling="random", reviewer_accuracy=accuracy)),
                (f"t1_{n}_acc{accuracy}_div", dict(kind="t1", n=n, rule="recall80", noise=noise, sampling="diversity", reviewer_accuracy=accuracy)),
            ]
    variants += [("cal", dict(kind="cal", noise=NOISE_RATE, stop="target", target=CAL_TARGET)),
                 ("cal_75", dict(kind="cal", noise=NOISE_RATE, stop="target", target=0.75)),
                 ("cal_perfect", dict(kind="cal", noise=0.0, stop="target", target=CAL_TARGET)),
                 ("cal_knee", dict(kind="cal", noise=NOISE_RATE, stop="knee", target=None))]
    if only:
        # a name or prefix (t1_100, cal), a suffix starting with "_" (_div, _noisy), the full accuracy
        # sweep, or just the newly added deep TREC points (perfect + accuracy sweep, random + diversity).
        if only == "new-depths":
            variants = [
                v for v in variants
                if v[1].get("n") in (7500, 10000)
                and (v[0].endswith("_div") or "reviewer_accuracy" in v[1] or (v[1]["noise"] == 0 and v[1]["sampling"] == "random" and v[1]["rule"] == "recall80"))
            ]
        elif only == "accuracy":
            variants = [v for v in variants if "reviewer_accuracy" in v[1]]
        else:
            variants = [v for v in variants if v[0] == only or v[0].startswith(only + "_") or (only.startswith("_") and v[0].endswith(only))]
    kw = _keyword_scores(Path(cfg["lexical"]), [d.id for d in pool]) if any(v[1]["kind"] == "cal" for v in variants) else None
    gold_eval_any = np.array([any(g.values()) for g in gold_eval.values()])

    for name, spec in variants:
        key = f"tar@{name}"
        runs = []
        n_seeds = seeds if spec["kind"] == "t1" else min(seeds, cfg["cal_seeds"])
        for seed in range(n_seeds):
            t1 = time.time()
            if spec["kind"] == "t1":
                sampling = spec.get("sampling", "random")
                if full_out is None:
                    dec, probs, meta = run_tar1(ts, pool, pool_idx, X, eval_docs, eval_idx, spec["n"], spec["rule"], spec["noise"], seed, exclude, sampling)
                    full_pos = None
                else:
                    # TREC: score the whole 286k collection once; the eval rows are a subset, the trec_full block gets the positives
                    full_dec, full_probs, meta = run_tar1(ts, pool, pool_idx, X, pool, np.arange(len(pool)), spec["n"], spec["rule"], spec["noise"], seed, exclude, sampling)
                    dec = {d.id: full_dec[d.id] for d in eval_docs}
                    probs = {q: full_probs[q][eval_idx] for q in ts.qids}
                    full_pos = [(d, q) for d, c in full_dec.items() for q, v in c.items() if v]
            else:
                keep = cal_pool(ts, pool, seed)
                sub = [pool[i] for i in keep]
                richness = sum(1 for d in sub if any(d.labels.get(q) == ts.positive_label for q in ts.qids)) / len(sub)
                n_ctrl = control_size(len(sub), richness, cfg["control"]) if spec["stop"] == "target" else None
                rev, s, meta = run_cal(ts, sub, X[keep], kw[keep], cfg["batch"], cfg["seed_n"], spec["noise"], seed, spec["stop"], spec["target"],
                                       n_ctrl, X[eval_idx], gold_eval_any, [d.id for d in eval_docs])
                sub_idx = {d.id: i for i, d in enumerate(sub)}
                ev = [d for d in eval_docs if d.id in sub_idx]  # on a downsampled pool the CAL rows cover the pool only
                dec = {}
                probs = {q: np.zeros(len(ev), dtype=np.float32) for q in ts.qids}
                p_all = sigmoid(s)
                for j, d in enumerate(ev):
                    c = rev.codes.get(d.id)
                    dec[d.id] = dict(c) if c else {q: False for q in ts.qids}
                    for q in ts.qids:
                        probs[q][j] = (1.0 if c[q] else 0.0) if c else p_all[sub_idx[d.id]] * 0.5
                meta["pool_ids"] = [d.id for d in sub] if len(sub) < len(pool) else None
                full_pos = [(d, q) for d, c in rev.codes.items() for q, v in c.items() if v] if full_out is not None else None
            m = doc_level(dec, {d: g for d, g in gold_eval.items() if d in dec})
            runs.append(dict(seed=seed, dec=dec, probs=probs, meta=meta, doc=m, full_pos=full_pos, docs=[d for d in eval_docs if d.id in dec]))
            extra = ""
            if spec["kind"] == "cal":
                cl = meta.get("classifier") or {}
                ev_cl = cl.get("eval") or {}
                extra = (f" est {meta['est_recall_at_stop']} reached {meta['reached_recall']:.3f} review-prec {meta['review_set_precision']:.3f}"
                         f" clf-eval r/p {ev_cl.get('recall')}/{ev_cl.get('precision')} ctrl {(meta.get('control_set') or {}).get('n')} | {meta['stop']}")
            console.print(f"  {key} seed {seed}: recall {m['recall'] if m['recall'] is None else round(m['recall'], 3)} precision {m['precision'] if m['precision'] is None else round(m['precision'], 3)} "
                          f"reviewed {meta['docs_reviewed']:,} ({meta['hours']:.1f} h, ${meta['cost_usd']:,.0f}) [{time.time() - t1:.0f}s]{extra}")
        runs.sort(key=lambda r: r["doc"]["f1"] or 0.0)
        med = runs[len(runs) // 2]
        rows = []
        for j, d in enumerate(med["docs"]):
            for q in ts.qids:
                rows.append(_row(d.id, q, key, med["dec"][d.id][q], float(med["probs"][q][j]), "tfidf-logreg"))
        _write(rows, out / corpus / "multi" / f"tar__{name}.jsonl")
        if full_out is not None and med["full_pos"] is not None:
            _write([_row(d, q, key, True, 1.0, "tfidf-logreg") for d, q in med["full_pos"]], full_out / f"tar__{name}.jsonl")
        side = {
            "corpus": corpus, "variant": name, "spec": spec, "n_eval": len(med["docs"]),
            "n_corpus": len(med["meta"]["pool_ids"]) if med["meta"].get("pool_ids") else len(pool),
            "reviewer": {"docs_per_hour": DOCS_PER_HOUR, "usd_per_hour": USD_PER_HOUR, "miscode_rate": spec["noise"]},
            "median_seed": med["seed"], "median": med["meta"],
            "seeds": [{"seed": r["seed"], "recall": r["doc"]["recall"], "precision": r["doc"]["precision"], "f1": r["doc"]["f1"],
                       "docs_reviewed": r["meta"]["docs_reviewed"], "hours": r["meta"]["hours"], "cost_usd": r["meta"]["cost_usd"],
                       **({"est_recall_at_stop": r["meta"].get("est_recall_at_stop"), "reached_recall": r["meta"].get("reached_recall"),
                           "review_set_precision": r["meta"].get("review_set_precision")} if spec["kind"] == "cal" else {})} for r in runs],
        }
        if spec["kind"] == "cal":
            side["plotted"] = "production set on pool"
            side["control_set"] = med["meta"].get("control_set")
        (out / corpus / "multi" / f"tar__{name}.tar.json").write_text(json.dumps(side, indent=1))
        console.print(f"[{corpus}] wrote {key} (median seed {med['seed']})")

"""Classical TAR baselines: a human reviewer plus a TF-IDF / logistic-regression classifier.

Two workflows, both simulated against the gold labels (the "reviewer" codes a document by reading its
gold labels, optionally with a miscoding rate):

  TAR 1.0  (simple learning)   The reviewer codes a random training sample of N documents. One
           classifier per issue plus one for "responsive to any issue" is trained on it. A cutoff is
           chosen by 5-fold cross-validation on the training sample alone (no peeking at the rest),
           either targeting 80% recall or maximising F1. Output over the whole corpus = the reviewer's
           codes on the N training documents + the classifier's calls on the remainder.

  TAR 2.0  (continuous active learning)   Seed = random documents + the highest keyword-floor scores.
           Loop: train on everything coded, rank the uncoded, the reviewer codes the top batch, repeat.
           Stop by the knee method (Cormack & Grossman 2016): once the slope of the gain curve before its
           knee is >= 6x the slope after it, with a minimum effort of 10% of the collection. The `cal_mp`
           variant stops after two consecutive batches under 5% relevant instead. The review set (what
           the classifier queued) is what the site plots; the production set (what the reviewer coded
           relevant) is reported alongside.
           Mallinckrodt's benchmark sample is 61% rich by design; CAL there runs on a 10%-rich pool (all
           gold-negative emails plus a per-seed random draw of positives).

Reviewer economics: 50 documents/hour, $65/hour. Compute is negligible and not charged.

Layout mirrors the API runs so export.py can pick the rows up:
  results/<corpus>/multi/tar__<variant>.jsonl        Prediction rows for the median seed (by doc-level F1)
  results/<corpus>/multi/tar__<variant>.tar.json     sidecar: review effort, cutoffs, spread across seeds
  results/trec_full/multi/tar__<variant>.jsonl       TREC: positive rows only over the 286k collection

Variants: t1_<N> (80%-recall cutoff, perfect reviewer), t1_<N>_f1 (F1 cutoff), t1_<N>_noisy (imperfect
reviewer: misses 10% of relevant, over-codes 2% of non-relevant), cal, cal_noisy, cal_mp.
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
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

from .providers.base import Prediction
from .tasks import Document, TaskSet, load_corpus

console = Console(width=200)

DOCS_PER_HOUR = 50.0
USD_PER_HOUR = 65.0
SEEDS = 5
MIN_POS_FOR_ISSUE_MODEL = 5
CAL_STOP_RATE = 0.05
CAL_STOP_PATIENCE = 2
KNEE_SLOPE_RATIO = 6.0
KNEE_MIN_EFFORT = 0.10
CAL_RICHNESS_CAP = 0.15  # pools richer than this are downsampled to CAL_TARGET_RICHNESS for the CAL rows
CAL_TARGET_RICHNESS = 0.10
NOISE_RATE = 0.10  # imperfect reviewer: misses 10% of relevant documents ...
NOISE_FP_RATIO = 0.2  # ... and over-codes 2% of non-relevant ones

# corpus key -> (task yaml, evaluation corpus, training/CAL pool, keyword-floor results, cal batch, cal seeds)
CORPORA = {
    "mnk": dict(task="tasks/mallinckrodt.yaml", eval="data/mallinckrodt/mnk.jsonl", pool=None, lexical="results/mnk/multi/lexical.jsonl", batch=50, seed_n=50, cal_seeds=SEEDS, stages=[100, 300, 1000]),
    "cuad": dict(task="tasks/cuad.yaml", eval="data/cuad/cuad.jsonl", pool=None, lexical="results/cuad/multi/lexical.jsonl", batch=100, seed_n=100, cal_seeds=SEEDS, stages=[100, 1000, 5000]),
    "trec": dict(task="tasks/trec.yaml", eval="data/trec/eval.jsonl", pool="data/trec/full.jsonl", lexical="results/trec_full/multi/lexical.jsonl", batch=1000, seed_n=100, cal_seeds=3, stages=[100, 1000, 5000]),
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

def run_tar1(ts: TaskSet, pool: list[Document], pool_idx: dict[str, int], X, eval_docs: list[Document],
             eval_idx: np.ndarray, n_train: int, rule: str, noise: float, seed: int, exclude: set[str]) -> tuple[dict[str, dict[str, bool]], dict[str, np.ndarray], dict]:
    """Returns (decisions on eval docs keyed by id, per-issue probabilities on eval docs, run meta)."""
    rng = np.random.default_rng(seed)
    cand = np.array([i for i, d in enumerate(pool) if d.id not in exclude])
    train = rng.choice(cand, size=min(n_train, len(cand)), replace=False)
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
            "hours": rev.hours, "cost_usd": rev.cost, "docs_reviewed": rev.n_reviewed}
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


def run_cal(ts: TaskSet, pool: list[Document], X, kw_score: np.ndarray, batch: int, seed_n: int, noise: float, seed: int,
            stop: str) -> tuple[Reviewer, np.ndarray, dict]:
    """Continuous active learning over the pool. Returns the reviewer (its codes are the production set),
    the final relevance scores over the pool, and run meta. `stop` is "knee" or "mp" (marginal precision)."""
    rng = np.random.default_rng(seed)
    n = len(pool)
    gold_any = np.array([any(d.labels.get(q) == ts.positive_label for q in ts.qids) for d in pool])
    rev = Reviewer(ts, {d.id: d for d in pool}, noise, seed)
    coded = np.zeros(n, dtype=bool)
    seed_idx = list(rng.choice(n, size=min(seed_n, n), replace=False))
    kw_order = np.argsort(-kw_score)
    for i in kw_order:
        if len(seed_idx) >= 2 * seed_n:
            break
        if i not in seed_idx:
            seed_idx.append(int(i))
    for i in seed_idx:
        rev.code(pool[i].id); coded[i] = True
    y = np.zeros(n, dtype=int)
    for i in seed_idx:
        y[i] = any(rev.codes[pool[i].id].values())
    # a seed with no positives cannot train: keep drawing random batches (what a team would do)
    while y[coded].sum() == 0 and coded.sum() < n:
        more = rng.choice(np.flatnonzero(~coded), size=min(batch, int((~coded).sum())), replace=False)
        for i in more:
            rev.code(pool[i].id); coded[i] = True; y[i] = any(rev.codes[pool[i].id].values())
    curve = [{"reviewed": int(coded.sum()), "found": int(y[coded].sum()), "found_gold": int(gold_any[coded].sum())}]
    lean = 0
    why = "pool exhausted"
    s = np.full(n, -10.0, dtype=np.float32)
    t0 = time.time()
    while coded.sum() < n:
        clf = fit(X[coded], y[coded])
        s = scores(clf, X)
        s[coded] = -np.inf
        take = np.argsort(-s)[: min(batch, int((~coded).sum()))]
        hits = 0
        for i in take:
            c = rev.code(pool[i].id); coded[i] = True; y[i] = any(c.values()); hits += y[i]
        curve.append({"reviewed": int(coded.sum()), "found": int(y[coded].sum()), "found_gold": int(gold_any[coded].sum())})
        if stop == "mp":
            lean = lean + 1 if hits / len(take) < CAL_STOP_RATE else 0
            if lean >= CAL_STOP_PATIENCE:
                why = "two consecutive batches under 5% relevant"; break
        elif knee_stop(curve, n):
            why = f"knee method: pre-knee slope ≥ {KNEE_SLOPE_RATIO:g}× post-knee slope, after ≥ {KNEE_MIN_EFFORT:.0%} of the collection"; break
    meta = {"noise": noise, "seed": seed, "batch": batch, "seed_docs": len(seed_idx), "docs_reviewed": rev.n_reviewed,
            "hours": rev.hours, "cost_usd": rev.cost, "batches": len(curve) - 1, "stop_rule": stop, "stop": why,
            "found_gold": int(gold_any[coded].sum()), "relevant_in_pool": int(gold_any.sum()), "pool_richness": float(gold_any.mean()),
            "curve": [curve[i] for i in sorted(set(list(range(0, len(curve), max(1, len(curve) // 60))) + [len(curve) - 1]))],
            "fit_seconds": round(time.time() - t0, 1)}
    return rev, s, meta


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
    console.print(f"[{corpus}] {X.shape[1]:,} features in {time.time() - t0:.0f}s")
    full_out = out / "trec_full" / "multi" if corpus == "trec" else None
    exclude = {d.id for d in eval_docs} if cfg["pool"] else set()

    variants: list[tuple[str, dict]] = []
    for n in cfg["stages"]:
        variants += [(f"t1_{n}", dict(kind="t1", n=n, rule="recall80", noise=0.0)),
                     (f"t1_{n}_f1", dict(kind="t1", n=n, rule="f1", noise=0.0)),
                     (f"t1_{n}_noisy", dict(kind="t1", n=n, rule="recall80", noise=NOISE_RATE))]
    variants += [("cal", dict(kind="cal", noise=0.0, stop="knee")), ("cal_noisy", dict(kind="cal", noise=NOISE_RATE, stop="knee")),
                 ("cal_mp", dict(kind="cal", noise=0.0, stop="mp"))]
    if only:
        variants = [v for v in variants if v[0] == only or v[0].startswith(only + "_")]
    kw = _keyword_scores(Path(cfg["lexical"]), [d.id for d in pool]) if any(v[1]["kind"] == "cal" for v in variants) else None

    for name, spec in variants:
        key = f"tar@{name}"
        runs = []
        n_seeds = seeds if spec["kind"] == "t1" else min(seeds, cfg["cal_seeds"])
        for seed in range(n_seeds):
            t1 = time.time()
            if spec["kind"] == "t1":
                if full_out is None:
                    dec, probs, meta = run_tar1(ts, pool, pool_idx, X, eval_docs, eval_idx, spec["n"], spec["rule"], spec["noise"], seed, exclude)
                    full_pos = None
                else:
                    # TREC: score the whole 286k collection once; the eval rows are a subset, the trec_full block gets the positives
                    full_dec, full_probs, meta = run_tar1(ts, pool, pool_idx, X, pool, np.arange(len(pool)), spec["n"], spec["rule"], spec["noise"], seed, exclude)
                    dec = {d.id: full_dec[d.id] for d in eval_docs}
                    probs = {q: full_probs[q][eval_idx] for q in ts.qids}
                    full_pos = [(d, q) for d, c in full_dec.items() for q, v in c.items() if v]
            else:
                keep = cal_pool(ts, pool, seed)
                sub = [pool[i] for i in keep]
                rev, s, meta = run_cal(ts, sub, X[keep], kw[keep], cfg["batch"], cfg["seed_n"], spec["noise"], seed, spec["stop"])
                sub_idx = {d.id: i for i, d in enumerate(sub)}
                ev = [d for d in eval_docs if d.id in sub_idx]  # on a downsampled pool the CAL rows cover the pool only
                dec = {}
                probs = {q: np.zeros(len(ev), dtype=np.float32) for q in ts.qids}
                p_all = sigmoid(np.where(np.isfinite(s), s, 10.0))
                for j, d in enumerate(ev):
                    c = rev.codes.get(d.id)
                    dec[d.id] = dict(c) if c else {q: False for q in ts.qids}
                    for q in ts.qids:
                        probs[q][j] = (1.0 if c[q] else 0.0) if c else p_all[sub_idx[d.id]] * 0.5
                meta["reviewed_ids"] = sorted(rev.codes)
                meta["pool_ids"] = [d.id for d in sub] if len(sub) < len(pool) else None
                full_pos = [(d, q) for d, c in rev.codes.items() for q, v in c.items() if v] if full_out is not None else None
            m = doc_level(dec, {d: g for d, g in gold_eval.items() if d in dec})
            runs.append(dict(seed=seed, dec=dec, probs=probs, meta=meta, doc=m, full_pos=full_pos, docs=[d for d in eval_docs if d.id in dec]))
            console.print(f"  {key} seed {seed}: recall {m['recall'] if m['recall'] is None else round(m['recall'], 3)} precision {m['precision'] if m['precision'] is None else round(m['precision'], 3)} "
                          f"reviewed {meta['docs_reviewed']:,} ({meta['hours']:.1f} h, ${meta['cost_usd']:,.0f}) [{time.time() - t1:.0f}s]")
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
                       "docs_reviewed": r["meta"]["docs_reviewed"], "hours": r["meta"]["hours"], "cost_usd": r["meta"]["cost_usd"]} for r in runs],
        }
        (out / corpus / "multi" / f"tar__{name}.tar.json").write_text(json.dumps(side, indent=1))
        console.print(f"[{corpus}] wrote {key} (median seed {med['seed']})")

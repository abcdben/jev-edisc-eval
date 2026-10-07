"""Run-to-run determinism study.

Design: a fixed, stratified sample of documents is scored K times per model under identical
settings (the same ones the benchmark ran under, plus an optional temperature-0 arm for the LLMs
that accept it). Repeats live in results/<corpus>/<arm>/<model>__rep<k>.jsonl; the benchmark run
of the same documents counts as repeat 1 where the configuration is identical.

Strata (100 docs each): `gray` (at least one gold label flagged debatable), `pos` (responsive to at
least one issue, nothing gray), `neg` (responsive to nothing, nothing gray). Within each stratum,
documents touching the two hardest issues (the narrow ones used for the single-issue slice) are
taken first so those issues have enough positives to measure.
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

FOCUS = ("som_narrow", "dea_narrow")  # single-issue slice: the two narrow issues


def build_sample(src: Path, dst: Path, per_stratum: int = 100, focus_first: int = 40, seed: int = 20260920) -> dict:
    docs = [json.loads(l) for l in src.open()]
    rng = random.Random(seed)
    strata: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        pos = any(v == "responsive" for v in d["labels"].values())
        gray = bool(d.get("gray"))
        strata["gray" if gray else ("pos" if pos else "neg")].append(d)

    def touches_focus(d: dict) -> bool:
        return any(d["labels"].get(q) == "responsive" or q in (d.get("gray") or []) for q in FOCUS)

    chosen: list[dict] = []
    for name in ("gray", "pos", "neg"):
        pool = strata[name][:]
        rng.shuffle(pool)
        focus = [d for d in pool if touches_focus(d)][:focus_first] if name != "neg" else []
        rest = [d for d in pool if d not in focus]
        take = focus + rest[: per_stratum - len(focus)]
        for d in take:
            d = dict(d)
            d.setdefault("meta", {})["det_stratum"] = name
            chosen.append(d)

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w") as f:
        for d in chosen:
            f.write(json.dumps(d) + "\n")

    summary = {
        "n": len(chosen),
        "strata": dict(Counter(d["meta"]["det_stratum"] for d in chosen)),
        "positives_by_issue": dict(Counter(q for d in chosen for q, v in d["labels"].items() if v == "responsive")),
        "gray_by_issue": dict(Counter(q for d in chosen for q in (d.get("gray") or []))),
        "corpus_strata": {k: len(v) for k, v in strata.items()},
    }
    return summary


# ------------------------------------------------------------------------------------------------
# Analysis
# ------------------------------------------------------------------------------------------------

import math
import re
from itertools import combinations

import numpy as np

Key = tuple[str, str]  # (doc_id, question)

MODELS = [
    "jev@base", "jev@choice", "jev@score", "jev@state_string", "openai-decisions@predicate", "openai-decisions@choice", "laya@base", "laya@recipe",
    "claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash",
    "gemma3-12b", "lexical",
]
T0_MODELS = ["claude-haiku-4.5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash"]


def _wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(p, 4), round(max(0, c - h), 4), round(min(1, c + h), 4)]


def _load_run(path: Path, questions: set[str] | None = None) -> dict[Key, tuple[str, float | None]]:
    out: dict[Key, tuple[str, float | None]] = {}
    for line in path.open():
        r = json.loads(line)
        if r.get("error") or r.get("label") not in ("responsive", "not_responsive"):
            continue
        if questions and r["question"] not in questions:
            continue
        out[(r["doc_id"], r["question"])] = (r["label"], r.get("p_positive"))
    return out


def _runs_for(results: Path, arm: str, model: str, setting: str, sample_ids: set[str], questions: set[str] | None) -> list[tuple[str, dict[Key, tuple[str, float | None]]]]:
    """Ordered list of (tag, predictions) for one cell. Default setting: the benchmark run is rep1."""
    stem = model.replace("@", "__")
    runs: list[tuple[str, dict]] = []
    if setting == "default":
        orig = results / "mnk" / arm / f"{stem}.jsonl"
        if orig.exists():
            preds = {k: v for k, v in _load_run(orig, questions).items() if k[0] in sample_ids}
            covered = {k[0] for k in preds}
            if len(covered) >= 0.95 * len(sample_ids):
                runs.append(("rep1", preds))
        pat = re.compile(rf"^{re.escape(stem)}__rep(\d+)\.jsonl$")
    else:
        pat = re.compile(rf"^{re.escape(stem)}__t0_rep(\d+)\.jsonl$")
    d = results / "mnk_det" / arm
    if d.exists():
        for f in sorted(d.iterdir(), key=lambda p: p.name):
            m = pat.match(f.name)
            if m:
                runs.append((f"{'t0_' if setting == 't0' else ''}rep{m.group(1)}", _load_run(f, questions)))
    return runs


def _pairwise(labels: list[str]) -> float:
    """Probability that two runs drawn without replacement disagree."""
    k = len(labels)
    if k < 2:
        return 0.0
    c = Counter(labels)
    same = sum(v * (v - 1) for v in c.values())
    return 1 - same / (k * (k - 1))


def _prf(pred: dict[str, str], gold: dict[str, str], keys) -> tuple[float | None, float | None]:
    tp = fp = fn = 0
    for k in keys:
        p, g = pred[k] == "responsive", gold[k] == "responsive"
        tp += p and g; fp += p and not g; fn += (not p) and g
    return (tp / (tp + fn) if tp + fn else None, tp / (tp + fp) if tp + fp else None)


def analyze(results: Path, sample: Path, corpus_path: Path, questions_single: tuple[str, ...] = FOCUS) -> dict:
    docs = {json.loads(l)["id"]: json.loads(l) for l in sample.open()}
    sample_ids = set(docs)
    strata = {i: d["meta"]["det_stratum"] for i, d in docs.items()}
    corpus_strata = Counter()
    for l in corpus_path.open():
        d = json.loads(l)
        pos = any(v == "responsive" for v in d["labels"].values()); gray = bool(d.get("gray"))
        corpus_strata["gray" if gray else ("pos" if pos else "neg")] += 1
    sample_strata = Counter(strata.values())
    weight = {s: (corpus_strata[s] / sum(corpus_strata.values())) / (sample_strata[s] / len(strata)) for s in sample_strata}

    out: dict = {
        "sample": {"n_docs": len(docs), "strata": dict(sample_strata), "corpus_strata": dict(corpus_strata), "focus_issues": list(questions_single)},
        "cells": [],
    }
    rng = np.random.default_rng(7)
    for arm in ("multi", "single"):
        qset = set(questions_single) if arm == "single" else None
        for setting in ("default", "t0"):
            for model in (MODELS if setting == "default" else T0_MODELS):
                runs = _runs_for(results, arm, model, setting, sample_ids, qset)
                if len(runs) < 2:
                    continue
                common = set.intersection(*(set(r.keys()) for _, r in runs))
                common = {k for k in common if k[0] in sample_ids}
                if not common:
                    continue
                keys = sorted(common)
                gold = {k: ("responsive" if docs[k[0]]["labels"].get(k[1]) == "responsive" else "not_responsive") for k in keys}
                grayk = {k: k[1] in (docs[k[0]].get("gray") or []) for k in keys}
                labels = {k: [r[k][0] for _, r in runs] for k in keys}
                probs = {k: [r[k][1] for _, r in runs if r[k][1] is not None] for k in keys}

                flipped = {k for k in keys if len(set(labels[k])) > 1}
                pw = {k: _pairwise(labels[k]) for k in keys}
                spread = {k: (max(probs[k]) - min(probs[k])) if len(probs[k]) >= 2 else 0.0 for k in keys}
                identical = sum(1 for k in keys if len(probs[k]) == len(runs) and spread[k] < 1e-9)
                confident = {k for k in flipped if min(probs[k], default=0.5) <= 0.3 and max(probs[k], default=0.5) >= 0.7}

                # corpus-weighted flip rate (reweight strata to the full-corpus mix)
                w = np.array([weight[strata[k[0]]] for k in keys]); fl = np.array([k in flipped for k in keys], dtype=float)
                weighted_flip = float((w * fl).sum() / w.sum())
                # bootstrap CI for pairwise disagreement (decisions resampled)
                pwv = np.array([pw[k] for k in keys])
                boots = [pwv[rng.integers(0, len(pwv), len(pwv))].mean() for _ in range(1000)] if len(pwv) > 1 else [pwv.mean()]

                def sub(ks) -> dict:
                    ks = list(ks)
                    f = sum(1 for k in ks if k in flipped)
                    return {"n": len(ks), "flip": _wilson(f, len(ks)), "pairwise": round(float(np.mean([pw[k] for k in ks])), 4) if ks else None}

                cell: dict = {
                    "arm": arm, "setting": setting, "model": model, "k": len(runs), "runs": [t for t, _ in runs],
                    "n_decisions": len(keys), "n_docs": len({k[0] for k in keys}),
                    "decision_flip": _wilson(len(flipped), len(keys)),
                    "decision_flip_weighted": round(weighted_flip, 4),
                    "pairwise": [round(float(pwv.mean()), 4), round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)],
                    "identical_prob": _wilson(identical, len(keys)),
                    "prob_spread_median": round(float(np.median([spread[k] for k in keys])), 4),
                    "prob_spread_p95": round(float(np.percentile([spread[k] for k in keys], 95)), 4),
                    "confident_flip": _wilson(len(confident), len(keys)),
                    "confident_share_of_flips": round(len(confident) / len(flipped), 4) if flipped else None,
                    "by_issue": {q: sub(k for k in keys if k[1] == q) for q in sorted({k[1] for k in keys})},
                    "by_stratum": {s: sub(k for k in keys if strata[k[0]] == s) for s in ("gray", "pos", "neg")},
                    "by_gold": {
                        "gray": sub(k for k in keys if grayk[k]),
                        "positive": sub(k for k in keys if gold[k] == "responsive" and not grayk[k]),
                        "negative": sub(k for k in keys if gold[k] != "responsive" and not grayk[k]),
                    },
                }
                # run-to-run range of recall / precision and the majority-vote alternative
                recs, precs = [], []
                for _, r in runs:
                    rc, pr = _prf({k: r[k][0] for k in keys}, gold, keys)
                    recs.append(rc); precs.append(pr)
                maj = {k: Counter(labels[k]).most_common(1)[0][0] for k in keys}
                mrc, mpr = _prf(maj, gold, keys)
                rr = [x for x in recs if x is not None]; pp = [x for x in precs if x is not None]
                cell["recall_range"] = [round(min(rr), 4), round(max(rr), 4)] if rr else None
                cell["precision_range"] = [round(min(pp), 4), round(max(pp), 4)] if pp else None
                cell["majority"] = {"recall": round(mrc, 4) if mrc is not None else None, "precision": round(mpr, 4) if mpr is not None else None}
                if arm == "multi":
                    # document-level: responsive to any issue
                    dids = sorted({k[0] for k in keys})
                    dl = {d: [any(r[(d, q)][0] == "responsive" for q in {k[1] for k in keys if k[0] == d}) for _, r in runs] for d in dids}
                    dflip = sum(1 for d in dids if len(set(dl[d])) > 1)
                    cell["doc_flip"] = _wilson(dflip, len(dids))
                    cell["doc_pairwise"] = round(float(np.mean([_pairwise([str(x) for x in dl[d]]) for d in dids])), 4)
                out["cells"].append(cell)
    return out

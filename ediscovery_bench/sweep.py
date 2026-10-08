"""Export per-model threshold sweep curves to results/sweep.json (read by site/src/sweep.ts for the Studio's Model threshold slider).

findings.json scores every model at its own label (export.py _score: `p.label == pos`), so the site's fixed points are the
models' own operating points. This module re-cuts the same saved predictions at p(responsive) >= t for t in `thresholds`
(0.01 .. 0.99 in steps of 0.01 by default, `--step`; the Trade-off page draws the whole curve, and OpenAI Decisions returns its
probabilities on a 0.01 grid) and writes, per corpus, arm and model, the confusion counts the site needs to draw a recall/precision
point with its 95% Wilson interval at any of those thresholds:

    curves[<corpus key>][<arm>][<model key>] = {
        "all":    {"P": gold-positive documents, "N": gold-negative documents, "tp": [per threshold], "fp": [per threshold]},
        "nogray": the same with gray documents excluded (export.py _score exclude_gray),
        "issues": {<question>: {"P", "N", "tp", "fp"}},  per-issue decision counts, all gold (as findings' all.per_issue)
        "decisions": {"all": {...}, "nogray": {...}}      every decision pooled (findings' all.decision / nogray.decision)
    }

Document level (`all`, `nogray`) is export.py _score's rule: a document is called responsive at t if any of its issue probabilities
clears t, and it is gold-positive if any issue is; so the 0.50 point reproduces findings' doc figures where the model's label is p >= 0.5.

Counts, not rates: recall = tp / P, precision = tp / (tp + fp), fn = P - tp, tn = N - fp, and the site computes the Wilson
intervals with metrics.wilson's formula (z = 1.96), so the numbers agree with export.py's _ci / _prf to the same rounding.
The cells, documents, gold re-binding and gray rules are export.py's (CORPORA, MODELS, _variant_models, _rebind); models whose
label is not a cut on a probability (classical TAR, the keyword baseline) are left out, and the site keeps them fixed.

With `--check`, every exported cell is also scored at its own label (export.py _score) and compared with findings.json, so a
sweep is only published when the fixed points it moves away from are the ones on the site.
"""

from __future__ import annotations

import json
import math
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

from .export import CORPORA, FT_KEYS, MODELS, _rebind, _score, _variant_models
from .runner import load_predictions, parse_job_stem
from .scope import in_scope
from .tasks import TaskSet, load_corpus

DEFAULT_STEP = 0.01


def thresholds_for(step: float = DEFAULT_STEP) -> list[float]:
    """The thresholds swept at `step`: step, 2 step, ... up to but excluding 1 (0.01 .. 0.99 at the default; 0.05 .. 0.95 at 0.05)."""
    n = round(1 / step)
    return [round(step * i, 4) for i in range(1, n)]


THRESHOLDS = thresholds_for()
Z = 1.96
# Kinds whose label is a decision of its own (a reviewer's coding, a cutoff chosen on a sample, a keyword rule), not p >= 0.5.
FIXED_KINDS = {"tar", "baseline"}


def _p_ok(p) -> bool:
    return p is not None and not (isinstance(p, float) and math.isnan(p))


def _curve(pairs: list[tuple[float, bool]], thresholds: list[float] = THRESHOLDS) -> dict:
    """Confusion counts per threshold for (score, gold) pairs: tp[i], fp[i] at thresholds[i]; P, N the gold totals."""
    P = sum(1 for _, g in pairs if g); N = len(pairs) - P
    tp = [0] * len(thresholds); fp = [0] * len(thresholds)
    for s, g in pairs:
        # thresholds ascend: s clears every threshold up to the last one <= s (bisect), none after it
        k = bisect_right(thresholds, s)
        if k == 0:
            continue
        if g:
            for i in range(k): tp[i] += 1
        else:
            for i in range(k): fp[i] += 1
    return {"P": P, "N": N, "tp": tp, "fp": fp}


def _sweep(preds, ts, docs_by_id, thresholds: list[float] = THRESHOLDS) -> dict:
    """The curve sets for one cell, from the rows export.py _score scores (no error, gold bound, p present)."""
    pos = ts.positive_label
    ok = [p for p in preds if p.error is None and p.gold is not None and _p_ok(p.p_positive)]
    out: dict = {}
    decisions: dict = {}
    for name, exclude_gray in (("all", False), ("nogray", True)):
        rows = [p for p in ok if not p.gray] if exclude_gray else ok
        by_doc: dict[str, list] = defaultdict(list)
        for p in rows:
            by_doc[p.doc_id].append(p)
        pairs = []
        for d, rs in by_doc.items():
            if exclude_gray and docs_by_id[d].gray:
                continue
            # a document is called responsive at t if any of its issue probabilities clears t: max over the rows
            pairs.append((max(p.p_positive for p in rs), any(p.gold == pos for p in rs)))
        out[name] = _curve(pairs, thresholds)
        # every decision pooled (export.py _score's decision level)
        decisions[name] = _curve([(p.p_positive, p.gold == pos) for p in rows], thresholds)
    issues = {}
    for q in ts.qids:
        qs = [(p.p_positive, p.gold == pos) for p in ok if p.question == q]
        if qs:
            issues[q] = _curve(qs, thresholds)
    out["issues"] = issues
    out["decisions"] = decisions
    return out


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def export_sweep(out: Path = Path("results"), dest: Path = Path("results/sweep.json"), check: bool = True, arms: tuple[str, ...] = ("multi",), step: float = DEFAULT_STEP) -> Path:
    """`arms`: the multi arm alone by default (the arm the site's recall/precision charts draw; the single arm doubles the file).
    `step`: the threshold grid (thresholds_for); 0.01 writes about 1.9 MB for the multi arm, 0.05 about 0.4 MB. 0.5 must be on the grid."""
    thresholds = thresholds_for(step)
    if 0.5 not in thresholds:
        raise ValueError(f"step {step} does not put 0.5 on the grid; the site's published point is the 0.50 cut")
    root = Path(".")
    findings = None
    if check:
        fp = out / "findings.json"
        if fp.exists():
            findings = {(r["corpus"], r["tag"], r["arm"], r["model"]): r for r in json.loads(fp.read_text())["records"]}
        else:
            print(f"no {fp}: skipping the findings check")
    curves: dict = {}
    n_cells = n_checked = n_bad = 0
    differ_at_half: list[str] = []
    for corpus, task, data, tag, _display, _gold_kind in CORPORA:
        ts = TaskSet.load(root / task)
        docs = in_scope(corpus, load_corpus(root / data))
        docs_by_id = {d.id: d for d in docs}
        ckey = f"{corpus}#{tag}" if tag else corpus
        for arm in arms:
            d = out / corpus / arm
            if not d.exists():
                continue
            files = {parse_job_stem(f.stem): f for f in d.glob("*.jsonl")}
            todo: list[tuple[str, str, dict, bool]] = []
            for key, meta in MODELS.items():
                todo.append((key, FT_KEYS.get(corpus) if key == "laya-ft" else key, meta, True))
            primary_mks = {mk for _, mk, _, _ in todo}
            for mk, meta in _variant_models().items():
                if mk not in primary_mks and (mk, tag) in files:
                    todo.append((mk, mk, meta, False))
            for key, mk, meta, primary in todo:
                if meta["kind"] in FIXED_KINDS or mk.startswith("tar@"):
                    continue
                f = files.get((mk, tag))
                if f is None:
                    continue
                preds = _rebind(load_predictions(f), docs_by_id, ts)
                if not preds:
                    continue
                if not primary and len({p.doc_id for p in preds}) < 0.98 * len(docs):
                    continue  # export.py: stalled cells are not exported
                cell = _sweep(preds, ts, docs_by_id, thresholds)
                curves.setdefault(ckey, {}).setdefault(arm, {})[key] = cell
                n_cells += 1
                if findings is not None:
                    rec = findings.get((corpus, tag, arm, key))
                    if rec is None:
                        print(f"  {ckey}/{arm}/{key}: not in findings.json")
                        n_bad += 1
                        continue
                    n_checked += 1
                    own = {"all": _score(preds, ts, docs_by_id, False), "nogray": _score(preds, ts, docs_by_id, True)}
                    for g in ("all", "nogray"):
                        for lvl in ("doc", "decision"):
                            for m in ("recall", "precision"):
                                if not _same(own[g][lvl][m], rec[g][lvl][m]):
                                    print(f"  MISMATCH {ckey}/{arm}/{key} {g}.{lvl}.{m}: {own[g][lvl][m]} != findings {rec[g][lvl][m]}")
                                    n_bad += 1
                    # where the model's own label is not p >= 0.5, the curve's 0.50 point is not the published point; the site shows the published one there
                    i50 = thresholds.index(0.5)
                    c = cell["all"]; doc = own["all"]["doc"]
                    if c["tp"][i50] != doc["tp"] or c["fp"][i50] != doc["fp"]:
                        differ_at_half.append(f"{ckey}/{arm}/{key} (label: tp {doc['tp']} fp {doc['fp']}; p>=0.5: tp {c['tp'][i50]} fp {c['fp'][i50]})")
    payload = {"thresholds": thresholds, "z": Z, "default": 0.5, "curves": curves}
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"{n_cells} cells; findings check: {n_checked} compared, {n_bad} mismatches")
    if differ_at_half:
        print(f"{len(differ_at_half)} cells whose own label differs from p >= 0.5 (the site keeps the published point at 0.50):")
        for s in differ_at_half:
            print(f"  {s}")
    return dest

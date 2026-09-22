"""Export the headline findings (speed, cost, recall/precision with CIs) to results/findings.json.

One record per (corpus, criteria version, arm, model). Every metric is computed from the saved
predictions with gold re-bound from the corpus file, so the JSON is reproducible from results/.

Definitions
  decision      one (document, issue) judgment
  doc-level     a document is responsive if it is gold-positive for ANY issue in the task set; the
                model's call is responsive if it labeled ANY issue positive (the "relevance" view)
  CIs           95% Wilson score intervals. Every document in each test set carries a gold label, so
                recall's interval is over the gold-positive set and precision's over the model's
                predicted-positive set (no sampling step).
  speed         median per-document wall time of the model's own calls, single stream: one call per
                document in the multi arm, the sum of the per-issue calls in the single arm. Laya's
                figure comes from the dedicated concurrency-1 latency runs where they exist.
  cost          sum of the model's per-decision cost over the documents, divided by documents.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .metrics import wilson
from .runner import load_predictions, parse_job_stem
from .tasks import TaskSet, load_corpus

CORPORA = [
    # key, task, data, tag, display, kind of gold
    ("veridian", "tasks/veridian.yaml", "data/veridian/veridian.jsonl", "", "Veridian (synthetic MDL)", "planner intent + text audit"),
    ("mnk", "tasks/mallinckrodt.yaml", "data/mallinckrodt/mnk.jsonl", "", "Mallinckrodt (opioid emails)", "LLM panel"),
    ("cuad", "tasks/cuad.yaml", "data/cuad/cuad.jsonl", "", "CUAD (contract clauses)", "human expert"),
    ("trec", "tasks/trec.yaml", "data/trec/eval.jsonl", "", "TREC 2016 (Jeb Bush email)", "NIST assessors"),
    ("trec", "tasks/trec.yaml", "data/trec/eval.jsonl", "v0", "TREC 2016 (Jeb Bush email)", "NIST assessors"),
]

MODELS: dict[str, dict] = {
    "jev@base":             dict(name="Jev 1.13", family="Jev", kind="system1"),
    "jev@state_string":     dict(name="Jev 1.13 (recipe)", family="Jev", kind="system1"),
    "laya@base":            dict(name="Laya", family="Laya", kind="system1"),
    "laya@recipe":          dict(name="Laya (recipe)", family="Laya", kind="system1"),
    "laya-ft":              dict(name="Laya fine-tuned", family="Laya", kind="system1_ft"),
    "claude-haiku-4.5":     dict(name="Claude Haiku 4.5", family="Anthropic", kind="llm"),
    "claude-sonnet-5":      dict(name="Claude Sonnet 5", family="Anthropic", kind="llm"),
    "gpt-5.6-luna":         dict(name="GPT-5.6 Luna", family="OpenAI", kind="llm"),
    "gpt-5.6-terra":        dict(name="GPT-5.6 Terra", family="OpenAI", kind="llm"),
    "gemini-3.5-flash-lite": dict(name="Gemini 3.5 Flash-Lite", family="Google", kind="llm"),
    "gemini-3.8-flash":     dict(name="Gemini 3.8 Flash", family="Google", kind="llm"),
    "gemma3-12b":           dict(name="Gemma 3 12B (local)", family="Google", kind="local_llm"),
    "lexical":              dict(name="Keyword baseline", family="baseline", kind="baseline"),
    # classical TAR: simulated reviewer (50 docs/h, $65/h) + TF-IDF / logistic regression, see tar.py
    "tar@t1_100":           dict(name="TAR 1.0 · 100 reviewed", family="TAR", kind="tar"),
    "tar@t1_300":           dict(name="TAR 1.0 · 300 reviewed", family="TAR", kind="tar"),
    "tar@t1_1000":          dict(name="TAR 1.0 · 1,000 reviewed", family="TAR", kind="tar"),
    "tar@t1_5000":          dict(name="TAR 1.0 · 5,000 reviewed", family="TAR", kind="tar"),
    "tar@t1_100_div":       dict(name="TAR 1.0 · 100 reviewed · diverse", family="TAR", kind="tar"),
    "tar@t1_300_div":       dict(name="TAR 1.0 · 300 reviewed · diverse", family="TAR", kind="tar"),
    "tar@t1_1000_div":      dict(name="TAR 1.0 · 1,000 reviewed · diverse", family="TAR", kind="tar"),
    "tar@t1_5000_div":      dict(name="TAR 1.0 · 5,000 reviewed · diverse", family="TAR", kind="tar"),
    "tar@cal":              dict(name="TAR 2.0 · CAL (80% target)", family="TAR", kind="tar"),
}
FT_KEYS = {"veridian": "laya-ft-veridian@recipe", "mnk": "laya-ft-mnk@recipe", "cuad": "laya-ft-cuad@recipe", "trec": "laya-ft-trec@recipe"}

# Ablation variants (one lever changed from the base configuration). Exported alongside the primary
# roster so a viewer can compare them; `primary` marks the rows meant for the headline comparison.
JEV_LEVERS = {
    "base": "Default: Noul question, prose criteria, RFP phrasing, matter context, structured state",
    "choice": "Question form: Choice over the two labels instead of Noul",
    "score": "Question form: Score (0-10 strength), rescaled to a probability",
    "crit_none": "Criteria: bare question, no positive/negative descriptions",
    "crit_struct": "Criteria: structured includes/excludes lists instead of prose",
    "literal": "Phrasing: the literal question instead of RFP language",
    "no_context": "Context: matter background paragraph removed",
    "state_string": "State: one flat string instead of structured fields",
    "gate": "Gating: corpus gate question first; not-responsive short-circuits",
    "ensemble": "Ensemble: mean over 3 phrasings",
    "decompose": "Decomposition: OR over subpart questions where defined",
    "preview": "Model: jev-preview checkpoint instead of jev-1.13.0",
}
LAYA_LEVERS = {
    "base": "Default configuration, 512-token context",
    "choice": "Question form: Choice over the two labels",
    "score": "Question form: Score (0-10), rescaled",
    "literal": "Phrasing: the literal question",
    "gate": "Gating: corpus gate question first",
    "ensemble": "Ensemble: mean over 3 phrasings",
    "decompose": "Decomposition: OR over subparts",
    "compact": "Compact: one-line instruction and one-sentence criteria that fit the context",
    "chunk": "Chunk: sliding window over the document, max-pooled",
    "recipe": "Compact + chunk",
    "recipe_choice": "Compact + chunk, Choice form",
}
TAR_LEVERS = {
    "t1": "TAR 1.0: the reviewer codes {n} random documents; classifier cutoff targets 80% recall (5-fold CV on the sample)",
    "t1_f1": "TAR 1.0, {n} reviewed: cutoff maximises F1 on the sample instead of targeting 80% recall",
    "t1_noisy": "TAR 1.0, {n} reviewed: imperfect reviewer (misses 10% of relevant documents, over-codes 2% of non-relevant)",
    "t1_div": "TAR 1.0, {n} reviewed: training sample chosen by cluster-stratified diversity sampling (SVD + k-means, one document per cluster) instead of at random; cutoff chosen the same way, but the coded sample is no longer random so its recall estimate is only a guide",
    "cal": "TAR 2.0: continuous active learning with an imperfect reviewer (misses 10% of relevant, over-codes 2% of non-relevant); stops when a random control set estimates 80% recall for two consecutive batches; plotted as the production set the reviewer coded relevant",
    "cal_75": "TAR 2.0, control-set stop at a 75% recall target instead of 80%",
    "cal_perfect": "TAR 2.0, 80% target, perfect reviewer (codes every document exactly as the gold labels)",
    "cal_knee": "TAR 2.0, imperfect reviewer, knee-method stop (Cormack & Grossman 2016) instead of the control-set recall target; no control set",
}
LAYA_CHECKPOINTS = {"laya": "English checkpoint", "laya-typed": "Typed checkpoint", "laya-multilingual": "Multilingual checkpoint"}


def _variant_models() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for v, desc in JEV_LEVERS.items():
        out[f"jev@{v}"] = dict(name=f"Jev · {v}", family="Jev", kind="system1", group="jev", variant=v, lever=desc)
    for ck, ckname in LAYA_CHECKPOINTS.items():
        for v, desc in LAYA_LEVERS.items():
            out[f"{ck}@{v}"] = dict(name=f"Laya {ckname.split()[0].lower()} · {v}" if ck != "laya" else f"Laya · {v}",
                                    family="Laya", kind="system1", group=ck, variant=v, lever=f"{ckname}. {desc}")
    for n in (100, 300, 1000, 5000):
        out[f"tar@t1_{n}"] = dict(name=f"TAR 1.0 · {n:,} reviewed", family="TAR", kind="tar", group="tar", variant=f"t1_{n}", lever=TAR_LEVERS["t1"].format(n=f"{n:,}"))
        out[f"tar@t1_{n}_f1"] = dict(name=f"TAR 1.0 · {n:,} · F1 cutoff", family="TAR", kind="tar", group="tar", variant=f"t1_{n}_f1", lever=TAR_LEVERS["t1_f1"].format(n=f"{n:,}"))
        out[f"tar@t1_{n}_noisy"] = dict(name=f"TAR 1.0 · {n:,} · 90% reviewer", family="TAR", kind="tar", group="tar", variant=f"t1_{n}_noisy", lever=TAR_LEVERS["t1_noisy"].format(n=f"{n:,}"))
        out[f"tar@t1_{n}_div"] = dict(name=f"TAR 1.0 · {n:,} · diverse", family="TAR", kind="tar", group="tar", variant=f"t1_{n}_div", lever=TAR_LEVERS["t1_div"].format(n=f"{n:,}"))
    out["tar@cal"] = dict(name="TAR 2.0 · CAL (80% target)", family="TAR", kind="tar", group="tar", variant="cal", lever=TAR_LEVERS["cal"])
    out["tar@cal_75"] = dict(name="TAR 2.0 · CAL · 75% target", family="TAR", kind="tar", group="tar", variant="cal_75", lever=TAR_LEVERS["cal_75"])
    out["tar@cal_perfect"] = dict(name="TAR 2.0 · CAL · perfect reviewer", family="TAR", kind="tar", group="tar", variant="cal_perfect", lever=TAR_LEVERS["cal_perfect"])
    out["tar@cal_knee"] = dict(name="TAR 2.0 · CAL · knee stop", family="TAR", kind="tar", group="tar", variant="cal_knee", lever=TAR_LEVERS["cal_knee"])
    for corpus in FT_KEYS:
        for v in ("compact", "recipe"):
            out[f"laya-ft-{corpus}@{v}"] = dict(name=f"Laya fine-tuned · {v}", family="Laya", kind="system1_ft", group="laya-ft", variant=v,
                                                 lever=f"SUPERVISED on the {corpus} dev split. {LAYA_LEVERS[v]}")
    return out


def _ci(k: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    lo, hi = wilson(k, n)
    return [round(k / n, 4), round(lo, 4), round(hi, 4)]


def _prf(tp: int, fp: int, fn: int, tn: int) -> dict:
    p = _ci(tp, tp + fp); r = _ci(tp, tp + fn)
    f1 = None if p is None or r is None or (p[0] + r[0]) == 0 else round(2 * p[0] * r[0] / (p[0] + r[0]), 4)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": p, "recall": r, "f1": f1,
            "elusion": _ci(fn, fn + tn), "n": tp + fp + fn + tn}


def _confusion(pairs) -> tuple[int, int, int, int]:
    tp = fp = fn = tn = 0
    for pred, gold in pairs:
        if pred and gold: tp += 1
        elif pred and not gold: fp += 1
        elif not pred and gold: fn += 1
        else: tn += 1
    return tp, fp, fn, tn


def _score(preds, ts, docs_by_id, exclude_gray: bool) -> dict:
    pos = ts.positive_label
    ok = [p for p in preds if p.error is None and p.gold is not None]
    if exclude_gray:
        ok = [p for p in ok if not p.gray]
    # decision level
    dec = _prf(*_confusion((p.label == pos, p.gold == pos) for p in ok))
    # per issue
    per_q = {}
    for q in ts.qids:
        qs = [p for p in ok if p.question == q]
        if qs:
            m = _prf(*_confusion((p.label == pos, p.gold == pos) for p in qs))
            per_q[q] = {"recall": m["recall"], "precision": m["precision"], "n_pos": m["tp"] + m["fn"], "n": m["n"]}
    # doc level: any issue
    by_doc: dict[str, list] = defaultdict(list)
    for p in ok:
        by_doc[p.doc_id].append(p)
    pairs = []
    for d, rows in by_doc.items():
        if exclude_gray and docs_by_id[d].gray:
            continue
        pairs.append((any(p.label == pos for p in rows), any(p.gold == pos for p in rows)))
    doc = _prf(*_confusion(pairs))
    return {"decision": dec, "doc": doc, "per_issue": per_q}


def _ops(preds, arm: str, latency_preds=None, latency_note: str | None = None, latency_scale: float | None = 1.0) -> dict:
    ok = [p for p in preds if p.error is None]
    by_doc: dict[str, list] = defaultdict(list)
    for p in ok:
        by_doc[p.doc_id].append(p)
    n_docs = len(by_doc)
    cost = sum(p.cost_usd for p in ok); lcost = sum(p.list_cost_usd for p in ok)
    tin = sum(p.input_tokens for p in ok); tout = sum(p.output_tokens for p in ok)
    src = latency_preds if latency_preds else ok
    lb: dict[str, list] = defaultdict(list)
    for p in src:
        if p.error is None and p.latency_ms is not None:
            lb[p.doc_id].append(p.latency_ms)
    per_doc = [max(v) if arm == "multi" else sum(v) for v in lb.values()]
    if latency_scale is None:
        per_doc = []  # no trustworthy per-call latency for this cell
    p50 = float(np.percentile(per_doc, 50)) * (latency_scale or 1) if per_doc else None
    p95 = float(np.percentile(per_doc, 95)) * (latency_scale or 1) if per_doc else None
    return {
        "n_docs": n_docs, "n_decisions": len(ok), "errors": sum(1 for p in preds if p.error),
        "cost_per_doc": cost / n_docs if n_docs else None, "list_cost_per_doc": lcost / n_docs if n_docs else None,
        "tokens_in_per_doc": tin / n_docs if n_docs else None, "tokens_out_per_doc": tout / n_docs if n_docs else None,
        "doc_latency_p50_ms": p50, "doc_latency_p95_ms": p95,
        "hours_per_100k_docs": (p50 * 100_000 / 3.6e6) if p50 else None,
        "latency_source": latency_note or ("dedicated concurrency-1 run" if latency_preds else "per-call latency from the main run"),
        "pricing_modes": sorted({p.pricing_mode for p in ok if p.pricing_mode}),
        "model_resolved": sorted({p.model_resolved for p in ok if p.model_resolved}),
    }


def _tar_block(side: dict) -> dict:
    """What the site needs from a TAR sidecar: the reviewer's effort on this corpus and the spread across seeds."""
    med = side["median"]; seeds = side["seeds"]
    rec = [x["recall"] for x in seeds if x["recall"] is not None]; prec = [x["precision"] for x in seeds if x["precision"] is not None]
    out = {
        "variant": side["variant"], "kind": side["spec"]["kind"], "n_corpus": side["n_corpus"], "n_eval": side["n_eval"],
        "docs_reviewed": med["docs_reviewed"], "hours": med["hours"], "cost_usd": med["cost_usd"],
        "review_share": med["docs_reviewed"] / side["n_corpus"],
        "reviewer": side["reviewer"], "seeds": len(seeds), "median_seed": side["median_seed"],
        "recall_range": [min(rec), max(rec)] if rec else None, "precision_range": [min(prec), max(prec)] if prec else None,
        "cutoff_rule": side["spec"].get("rule"), "sampling": side["spec"].get("sampling", "random" if side["spec"]["kind"] == "t1" else None),
        "sampling_meta": {k: med.get(k) for k in ("svd_dims", "svd_fit_rows", "k", "empty_clusters")} if med.get("sampling") == "diversity" else None,
        "issue_models": med.get("issue_models"), "train_positives_any": med.get("train_positives_any"),
        "batches": med.get("batches"), "batch": med.get("batch"), "stop": med.get("stop"), "stop_rule": med.get("stop_rule"), "curve": med.get("curve"),
        "pool_richness": med.get("pool_richness"), "relevant_in_pool": med.get("relevant_in_pool"), "found_gold": med.get("found_gold"),
        "downsampled": bool(med.get("pool_ids")),
    }
    if side["spec"]["kind"] == "cal":
        # CAL: the plotted set is the production set (what the reviewer coded relevant, control set included) on the
        # pool CAL ran over. The sidecar carries the process figures the tooltip shows next to it.
        out.update({
            "plotted": med.get("plotted", "production set on pool"), "target": med.get("target"),
            "docs_queued": med.get("docs_queued"), "control_set": med.get("control_set"),
            "est_recall_at_stop": med.get("est_recall_at_stop"), "reached_recall": med.get("reached_recall"),
            "review_set_precision": med.get("review_set_precision"), "production": med.get("production"),
            "classifier": med.get("classifier"),
        })
    return out


def _tar_ops(t: dict) -> dict:
    """Human review is the whole cost of a TAR workflow: hours and dollars scale with documents reviewed on
    THIS corpus, amortised over the corpus the workflow ran on (the 286k collection for TREC)."""
    n = t["n_corpus"]
    return {
        "cost_per_doc": t["cost_usd"] / n, "list_cost_per_doc": t["cost_usd"] / n,
        "tokens_in_per_doc": None, "tokens_out_per_doc": None,
        "doc_latency_p50_ms": t["hours"] * 3.6e6 / n, "doc_latency_p95_ms": None,
        "hours_per_100k_docs": t["hours"] * 1e5 / n,
        "latency_source": f"simulated reviewer at {t['reviewer']['docs_per_hour']:.0f} docs/hour, ${t['reviewer']['usd_per_hour']:.0f}/hour: "
                          f"{t['docs_reviewed']:,} of {n:,} documents reviewed ({t['hours']:.1f} h); compute not charged",
        "pricing_modes": ["human review"],
    }


def _rebind(preds, docs_by_id, ts):
    out = []
    for p in preds:
        d = docs_by_id.get(p.doc_id)
        if d is None:
            continue
        p.gold = d.gold(p.question, ts.negative_label); p.gray = p.question in d.gray
        if p.gold is not None:
            out.append(p)
    return out


def export(out: Path = Path("results"), dest: Path = Path("results/findings.json")) -> Path:
    root = Path(".")
    records = []
    corpora_meta = {}
    for corpus, task, data, tag, display, gold_kind in CORPORA:
        ts = TaskSet.load(root / task)
        docs = load_corpus(root / data)
        docs_by_id = {d.id: d for d in docs}
        pos = ts.positive_label
        n_pos_docs = sum(1 for d in docs if any(d.labels.get(q) == pos for q in ts.qids))
        corpora_meta[f"{corpus}#{tag}" if tag else corpus] = {
            "corpus": corpus, "tag": tag, "display": display, "gold": gold_kind, "n_docs": len(docs),
            "n_issues": len(ts.qids), "issues": {q: ts.questions[q].title for q in ts.qids},
            "n_pos_docs_any": n_pos_docs,
            "n_pos_by_issue": {q: sum(1 for d in docs if d.labels.get(q) == pos) for q in ts.qids},
            "n_gray_by_issue": {q: sum(1 for d in docs if q in d.gray) for q in ts.qids},
        }
        for arm in ("multi", "single"):
            d = out / corpus / arm
            if not d.exists():
                continue
            files = {parse_job_stem(f.stem): f for f in d.glob("*.jsonl")}
            todo: list[tuple[str, str, dict, bool]] = []  # (record key, model key, meta, primary)
            for key, meta in MODELS.items():
                todo.append((key, FT_KEYS.get(corpus) if key == "laya-ft" else key, meta, True))
            primary_mks = {mk for _, mk, _, _ in todo}
            for mk, meta in _variant_models().items():
                if mk not in primary_mks and (mk, tag) in files:
                    todo.append((mk, mk, meta, False))
            for key, mk, meta, primary in todo:
                f = files.get((mk, tag))
                if f is None:
                    continue
                preds = _rebind(load_predictions(f), docs_by_id, ts)
                if not preds:
                    continue
                if not primary and not mk.startswith("tar@") and len({p.doc_id for p in preds}) < 0.98 * len(docs):
                    continue  # stalled single-arm cells: partial files are not comparable (TAR/CAL pools are subsets by design)
                lat = files.get((mk, "latency"))
                lat_preds = _rebind(load_predictions(lat), docs_by_id, ts) if lat else None
                lat_note = None
                lat_scale: float | None = 1.0
                if lat_preds is None and mk.startswith("laya"):
                    # Not every Laya cell has a dedicated concurrency-1 sample (TREC has none; the
                    # fine-tuned checkpoints and most ablation variants have none). Borrow the closest
                    # A100 sample rather than report batched-queue latency from the concurrency-64 grid
                    # as per-call latency. Variants that make the same number of forward passes as the
                    # default borrow the default's sample; the ensemble makes three; chunking is what
                    # the recipe does; decomposition has no clean proxy and is left blank.
                    ck, _, var = mk.partition("@")
                    if ck.startswith("laya-ft"):
                        proxies, lat_scale = ["laya@recipe"], 1.0
                    elif var in ("base", "choice", "score", "literal", "gate", "compact"):
                        proxies, lat_scale = [f"{ck}@base", "laya@base"], 1.0
                    elif var == "ensemble":
                        proxies, lat_scale = [f"{ck}@base", "laya@base"], 3.0
                    elif var in ("chunk", "recipe", "recipe_choice"):
                        proxies, lat_scale = [f"{ck}@recipe", "laya@recipe"], 1.0
                    else:
                        proxies, lat_scale = [], None
                    for proxy in proxies:
                        for other in (corpus, "cuad", "veridian", "mnk"):
                            alt = out / other / arm / f"{proxy.replace('@', '__')}__latency.jsonl"
                            if alt.exists():
                                lat_preds = [p for p in load_predictions(alt) if p.error is None]
                                what = "this model" if proxy == mk else f"{proxy} (same forward pass{'es ×3' if lat_scale == 3.0 else ''})"
                                where = "this corpus" if other == corpus else f"{other} (none run on this corpus)"
                                lat_note = f"concurrency-1 sample of {what} on {where}"
                                break
                        if lat_preds is not None:
                            break
                    if lat_preds is None:
                        lat_note = "no concurrency-1 sample for this configuration; grid latency was contended and is not reported"
                        lat_scale = None
                # the fine-tuned model was evaluated on a held-out split only: restrict the doc universe
                ids = {p.doc_id for p in preds}
                var_meta = _variant_models().get(mk, {})
                rec = {
                    "corpus": corpus, "tag": tag, "arm": arm, "model": key, "model_key": mk, **meta, "primary": primary,
                    "group": var_meta.get("group"), "variant": var_meta.get("variant"), "lever": var_meta.get("lever"),
                    "subset": None if len(ids) >= 0.98 * len(docs) else f"{len(ids)} of {len(docs)} docs",
                    "ops": _ops(preds, arm, lat_preds, lat_note, lat_scale),
                    "all": _score(preds, ts, docs_by_id, False),
                    "nogray": _score(preds, ts, docs_by_id, True),
                }
                side = f.with_suffix(".tar.json")
                if mk.startswith("tar@") and side.exists():
                    sj = json.loads(side.read_text())
                    rec["tar"] = _tar_block(sj)
                    rec["ops"].update(_tar_ops(rec["tar"]))
                rec["nogray"].pop("per_issue", None)  # keep the payload small; per-issue drill-down uses all gold
                for k in ("cost_per_doc", "list_cost_per_doc", "tokens_in_per_doc", "tokens_out_per_doc", "doc_latency_p50_ms", "doc_latency_p95_ms", "hours_per_100k_docs"):
                    if rec["ops"][k] is not None:
                        rec["ops"][k] = round(rec["ops"][k], 6 if "cost" in k else 2)
                records.append(rec)

    # Full TREC collection: 286k emails, three models. Gold outside the NIST-judged set is negative,
    # so recall is exact against the assessors' relevant set and precision is a lower bound.
    full = {}
    fdir = out / "trec_full" / "multi"
    if fdir.exists():
        ts = TaskSet.load(root / "tasks/trec.yaml")
        pos = ts.positive_label
        rel: dict[str, set[str]] = defaultdict(set)
        n_full = 0
        for line in (root / "data/trec/full.jsonl").open():
            d = json.loads(line); n_full += 1
            for q, v in d["labels"].items():
                if v == pos and q in ts.questions:  # full.jsonl also carries 2015-topic labels; ignore them
                    rel[q].add(d["id"])
        for f in fdir.glob("*.jsonl"):
            mk, tag = parse_job_stem(f.stem)
            if tag:
                continue
            flagged: dict[str, set[str]] = defaultdict(set)
            any_doc: set[str] = set()
            n_rows = 0
            for line in f.open():
                r = json.loads(line); n_rows += 1
                if r.get("error") is None and r["label"] == pos:
                    flagged[r["question"]].add(r["doc_id"]); any_doc.add(r["doc_id"])
            per_q = {}
            for q in ts.qids:
                tp = len(flagged[q] & rel[q])
                per_q[q] = {"recall": _ci(tp, len(rel[q])), "precision_lb": _ci(tp, len(flagged[q])), "flagged": len(flagged[q]), "relevant": len(rel[q])}
            rel_any = set().union(*rel.values())
            tp_any = len(any_doc & rel_any)
            full[mk] = {
                "n_docs": n_full, "n_rows": n_rows, "per_issue": per_q,
                "doc": {"flagged": len(any_doc), "relevant": len(rel_any), "recall": _ci(tp_any, len(rel_any)),
                        "precision_lb": _ci(tp_any, len(any_doc)), "review_share": len(any_doc) / n_full},
            }
    det_path = out / "determinism.json"
    determinism = json.loads(det_path.read_text()) if det_path.exists() else None
    payload = {"corpora": corpora_meta, "models": MODELS, "records": records, "trec_full": full, "determinism": determinism}
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    return dest

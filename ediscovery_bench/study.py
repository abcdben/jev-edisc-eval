"""Human-anchored study export -> results/study.json (read by site/study.html).

One file with an explicit schema so the interface can be built before the new runs exist:

- `datasets`     corpora, measured today or planned (TREC Legal 2009 / 2010)
- `arms`         models, classical TAR, and human reviewers, each with a kind
- `experiments`  the analyses; each names its chart type, its measures and which datasets it applies to
- `values`       values[dataset][experiment][arm][measure] -> {v, lo, hi, n, planned, note}

Measured cells are taken from findings.json (`bench export-findings`) and determinism.json. Cells for
experiments or datasets that have not been run yet are generated as *placeholders*: deterministic, plausible,
and flagged `planned: true` so the site hatches them. Replace `_placeholder` lookups with real computations as
the runs land; the schema and the site do not change.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------------------------------------ datasets

DATASETS: list[dict[str, Any]] = [
    dict(id="trec", label="TREC 2016", short="Jeb Bush emails, NIST labels", status="measured", findings="trec",
         human_signals=["single assessor"]),
    dict(id="mnk", label="Mallinckrodt", short="opioid-litigation emails, LLM-panel labels", status="measured", findings="mnk",
         human_signals=[]),
    dict(id="cuad", label="CUAD", short="commercial contracts, expert labels", status="measured", findings="cuad",
         human_signals=["consensus of trained annotators"]),
    dict(id="veridian", label="Veridian", short="synthetic medical-device MDL", status="measured", findings="veridian",
         human_signals=[]),
    # data/legal09/doc_ids.jsonl: 2009 Interactive assessments (pre/post adjudication) as an id manifest; the 2009 collection is not public,
    # so the labels cannot yet be joined to text. data/legal10/learn.jsonl carries the same 7 topics on EDRM v2 with a single assessment.
    dict(id="legal09", label="TREC Legal 2009", short="Enron emails · first-pass review + Topic Authority appeals · labels only, text pending", status="planned", findings=None,
         n_docs=49285, n_issues=7, gold="Topic Authority (adjudicated)",
         human_signals=["first-pass reviewer", "appeals", "adjudicator"]),
    # data/legal10/legal10.jsonl: 46,331 judged documents with text, 1,815 of them relabelled on appeal.
    dict(id="legal10", label="TREC Legal 2010", short="Enron emails · first-pass review + Topic Authority appeals", status="planned", findings=None,
         n_docs=46331, n_issues=4, gold="Topic Authority (adjudicated)",
         human_signals=["first-pass reviewer", "appeals", "adjudicator"]),
]
LEGAL = {"legal09", "legal10"}
MEASURED = {"trec", "mnk", "cuad", "veridian"}

# ------------------------------------------------------------------------------------------------ arms

ARMS: list[dict[str, Any]] = [
    # decision models
    dict(id="jev@base", name="Jev 1.13 · Noul", short="Jev · Noul", kind="system1", maker="TypeSafe", color="var(--c-jev)", status="measured"),
    dict(id="jev@choice", name="Jev 1.13 · Choice", short="Jev · Choice", kind="system1", maker="TypeSafe", color="var(--v3)", status="measured"),
    dict(id="jev@score", name="Jev 1.13 · Score", short="Jev · Score", kind="system1", maker="TypeSafe", color="var(--v5)", status="measured"),
    dict(id="openai-decisions", name="OpenAI Decisions (GPT-6 Luna)", short="OpenAI Decisions", kind="system1", maker="OpenAI", color="var(--v7)", status="planned",
         note="Decisions API, limited preview. Not yet run."),
    dict(id="tev1-4b", name="Together Tev1 4B", short="Tev1 4B", kind="system1", maker="Together", color="var(--v11)", status="planned",
         note="Choice-only decision model via OpenRouter. Not yet run."),
    dict(id="solar-decide", name="Upstage Solar Decide", short="Solar Decide", kind="system1", maker="Upstage", color="var(--v13)", status="planned",
         note="Jev-schema decision model via OpenRouter. Not yet run."),
    dict(id="laya-ft", name="Laya, fine-tuned", short="Laya (ft)", kind="system1_ft", maker="ConvAI", color="var(--c-laya-ft)", status="measured"),
    # LLMs
    dict(id="claude-haiku-4.5", name="Claude Haiku 4.5", short="Haiku 4.5", kind="llm", maker="Anthropic", color="var(--c-haiku)", status="measured"),
    dict(id="claude-sonnet-5", name="Claude Sonnet 5", short="Sonnet 5", kind="llm", maker="Anthropic", color="var(--c-sonnet)", status="measured"),
    dict(id="gpt-5.6-luna", name="GPT-5.6 Luna", short="GPT-5.6 Luna", kind="llm", maker="OpenAI", color="var(--c-luna)", status="measured"),
    dict(id="gpt-5.6-terra", name="GPT-5.6 Terra", short="GPT-5.6 Terra", kind="llm", maker="OpenAI", color="var(--c-terra)", status="measured"),
    dict(id="gemini-3.5-flash-lite", name="Gemini 3.5 Flash-Lite", short="Gemini 3.5 Flash-Lite", kind="llm", maker="Google", color="var(--c-flashlite)", status="measured"),
    dict(id="gemini-3.8-flash", name="Gemini 3.8 Flash", short="Gemini 3.8 Flash", kind="llm", maker="Google", color="var(--c-flash)", status="measured"),
    dict(id="gemma3-12b", name="Gemma 3 12B (local)", short="Gemma 3 12B", kind="local_llm", maker="Google", color="var(--c-gemma)", status="measured"),
    # classical TAR
    dict(id="tar@t1_1000_div", name="TAR 1.0 · 1,000 reviewed · diverse", short="TAR 1.0 · 1k", kind="tar", maker="TAR", color="var(--c-tar-3)", status="measured"),
    dict(id="tar@cal", name="TAR 2.0 · CAL (80% target)", short="TAR 2.0 · CAL", kind="tar", maker="TAR", color="var(--c-cal)", status="measured"),
    # humans
    dict(id="human@firstpass", name="First-pass reviewer", short="First-pass reviewer", kind="human", maker="Human", color="var(--ink-2)", status="planned",
         note="TREC Legal contract reviewers and law-student volunteers, scored against the Topic Authority. From the released pre-adjudication qrels."),
    dict(id="human@literature", name="Human reviewer (literature)", short="Reviewer (literature)", kind="human", maker="Human", color="var(--ink-3)", status="planned",
         note="Published figures: Roitblat et al. 2010 re-review agreement, TREC-4 inter-assessor overlap, industry throughput and rate cards. Not measured in this study."),
]
HUMAN = {a["id"] for a in ARMS if a["kind"] == "human"}

# ------------------------------------------------------------------------------------------------ experiments

def M(id: str, label: str, unit: str, higher: bool = True, **kw: Any) -> dict[str, Any]:
    return dict(id=id, label=label, unit=unit, higher_better=higher, **kw)

EXPERIMENTS: list[dict[str, Any]] = [
    dict(id="accuracy", group="Accuracy", title="Accuracy vs. the standard", chart="pr",
         question="How does each arm's recall and precision compare, scored against the same labels?",
         measures=[M("recall", "Recall", "pct"), M("precision", "Precision", "pct"), M("f1", "F1", "pct"), M("elusion", "Elusion", "pct", higher=False)],
         datasets=["trec", "mnk", "cuad", "veridian", "legal09", "legal10"],
         humans=["human@firstpass"]),
    dict(id="iso_recall", group="Accuracy", title="At the reviewer's operating point", chart="bars",
         question="Holding the model to the first-pass reviewer's recall, how much more precise is it, and how much of the collection would a human still read?",
         measures=[M("precision_at_human_recall", "Precision at reviewer recall", "pct"), M("review_fraction_at_human_recall", "Review fraction at reviewer recall", "pct", higher=False)],
         datasets=["legal09", "legal10"], humans=["human@firstpass"],
         na="Needs a first-pass human review of the same documents; only the TREC Legal collections have one."),
    dict(id="sides", group="Agreement", title="Whose side on contested documents", chart="grid",
         question="On documents whose first-pass label was appealed, does the model side with the reviewer or with the adjudicator?",
         measures=[M("agree_both", "Agrees with both", "pct"), M("sides_authority", "Sides with authority", "pct"), M("sides_reviewer", "Sides with reviewer", "pct", higher=False),
                   M("neither", "Disagrees with both", "pct", higher=False), M("kappa_authority", "κ vs. authority", "kappa"), M("kappa_reviewer", "κ vs. reviewer", "kappa"),
                   M("error_dependence", "P(wrong | reviewer wrong) / P(wrong)", "ratio", higher=False)],
         datasets=["legal09", "legal10"], humans=[],
         na="Needs appealed and adjudicated documents; only the TREC Legal collections publish them."),
    dict(id="contested", group="Agreement", title="Knows when humans disagree", chart="roc",
         question="Does low model confidence predict the documents humans contested?",
         measures=[M("auc_contested", "AUC: confidence vs. contested", "auc"), M("conf_gap", "Confidence gap, clear − contested", "pct")],
         datasets=["mnk", "veridian", "legal09", "legal10"], humans=[],
         na="Needs a per-document record of human disagreement (appeals, panel splits, gray flags)."),
    dict(id="consistency", group="Consistency", title="Consistency", chart="bars",
         question="How often does the same input get a different answer? Models re-run; humans re-review.",
         measures=[M("decision_flip", "Decision flip rate", "pct", higher=False), M("doc_flip", "Document flip rate", "pct", higher=False), M("identical_prob", "Identical probability", "pct")],
         datasets=["mnk", "legal10"], humans=["human@literature"],
         na="Repeat runs exist for the Mallinckrodt determinism sample; TREC Legal 2010 has a redundantly assessed slice."),
    dict(id="bias", group="Bias", title="Systematic bias", chart="bars",
         question="Does the arm over- or under-call responsiveness, and does accuracy depend on document length?",
         measures=[M("prevalence_ratio", "Predicted / true prevalence", "ratio"), M("recall_long_minus_short", "Recall, long − short documents", "pct")],
         datasets=["trec", "mnk", "cuad", "veridian", "legal09", "legal10"], humans=["human@firstpass"]),
    dict(id="workflow", group="Workflow", title="Workflow simulation", chart="frontier",
         question="Recall against human hours for human-only, model-only, and hybrid review of the same collection.",
         measures=[M("recall", "Recall", "pct"), M("human_share", "Documents read by a human", "pct", higher=False), M("hours_per_100k", "Human hours per 100k", "hours", higher=False),
                   M("usd_per_100k", "Cost per 100k", "usd", higher=False)],
         datasets=["legal09", "legal10"], humans=["human@firstpass"],
         na="Simulated on the TREC Legal collections, following Cormack & Grossman's adjudicated-QC design."),
    dict(id="speed_cost", group="Speed & cost", title="Speed and cost", chart="bars",
         question="Median seconds per document and dollars per 100,000 documents, with a human reviewer's throughput and rate for scale.",
         measures=[M("latency_p50_ms", "Median latency per document", "ms", higher=False), M("usd_per_100k", "Cost per 100k documents", "usd", higher=False),
                   M("hours_per_100k", "Hours per 100k documents", "hours", higher=False)],
         datasets=["trec", "mnk", "cuad", "veridian", "legal09", "legal10"], humans=["human@literature"]),
]

# ------------------------------------------------------------------------------------------------ placeholders

def _u(*parts: Any) -> float:
    """Deterministic uniform(0,1) from the cell's identity, so placeholders are stable across exports."""
    h = hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:12], 16) / 16**12

def _jit(center: float, spread: float, *key: Any) -> float:
    return center + (2 * _u(*key) - 1) * spread

# Plausible centres by kind, used only for planned cells. Humans from the TREC Legal / Roitblat literature; models from today's measured rows.
KIND_CENTER: dict[str, dict[str, float]] = {
    "system1":    dict(recall=0.80, precision=0.78, flip=0.01, latency=200, usd=20, auc=0.78, prev=1.03),
    "system1_ft": dict(recall=0.84, precision=0.80, flip=0.00, latency=30, usd=5, auc=0.72, prev=1.00),
    "llm":        dict(recall=0.86, precision=0.72, flip=0.05, latency=2500, usd=900, auc=0.66, prev=1.15),
    "local_llm":  dict(recall=0.78, precision=0.66, flip=0.06, latency=4000, usd=120, auc=0.60, prev=1.20),
    "tar":        dict(recall=0.80, precision=0.55, flip=0.03, latency=0, usd=1500, auc=0.55, prev=1.30),
    "human":      dict(recall=0.66, precision=0.62, flip=0.27, latency=72000, usd=6000, auc=0.50, prev=1.10),
}

def _placeholder(ds: str, ex: str, arm: dict[str, Any], mid: str) -> dict[str, Any] | None:
    k = arm["kind"]; c = KIND_CENTER[k]; key = (ds, ex, arm["id"], mid)
    cell: dict[str, Any] = dict(planned=True)
    def ci(v: float, w: float, lo0: float = 0.0, hi0: float = 1.0) -> None:
        cell.update(v=round(min(hi0, max(lo0, v)), 4), lo=round(max(lo0, v - w), 4), hi=round(min(hi0, v + w), 4), n=3000)
    if mid == "recall": ci(_jit(c["recall"], 0.06, *key), 0.03)
    elif mid == "precision": ci(_jit(c["precision"], 0.06, *key), 0.03)
    elif mid == "f1":
        r = _jit(c["recall"], 0.06, ds, ex, arm["id"], "recall"); p = _jit(c["precision"], 0.06, ds, ex, arm["id"], "precision")
        ci(2 * r * p / (r + p), 0.03)
    elif mid == "elusion": ci(_jit((1 - c["recall"]) * 0.35, 0.03, *key), 0.015)
    elif mid == "precision_at_human_recall": ci(_jit(c["precision"] + 0.08, 0.05, *key), 0.03)
    elif mid == "review_fraction_at_human_recall": ci(_jit(0.35 if k != "human" else 1.0, 0.08 if k != "human" else 0, *key), 0.02)
    elif mid == "agree_both": ci(_jit(0.18, 0.05, *key), 0.03)
    elif mid == "sides_authority": ci(_jit(0.62 if k in ("system1", "llm", "system1_ft") else 0.45, 0.08, *key), 0.03)
    elif mid == "sides_reviewer": ci(_jit(0.14, 0.05, *key), 0.03)
    elif mid == "neither": ci(_jit(0.06, 0.03, *key), 0.02)
    elif mid == "kappa_authority": ci(_jit(0.62, 0.08, *key), 0.04, -1, 1)
    elif mid == "kappa_reviewer": ci(_jit(0.48, 0.08, *key), 0.04, -1, 1)
    elif mid == "error_dependence": ci(_jit(1.6 if k != "human" else 2.4, 0.3, *key), 0.15, 0, 10)
    elif mid == "auc_contested": ci(_jit(c["auc"], 0.04, *key), 0.02, 0.5, 1)
    elif mid == "conf_gap": ci(_jit(0.22 if k == "system1" else 0.10, 0.05, *key), 0.03, -1, 1)
    elif mid == "decision_flip": ci(_jit(c["flip"], c["flip"] * 0.4, *key), 0.004)
    elif mid == "doc_flip": ci(_jit(c["flip"] * (1.3 if k == "human" else 3.5), c["flip"] * 0.3, *key), 0.01)
    elif mid == "identical_prob": ci(_jit(0.5 if k == "system1" else 0.12, 0.05, *key), 0.02)
    elif mid == "prevalence_ratio": ci(_jit(c["prev"], 0.08, *key), 0.04, 0, 5)
    elif mid == "recall_long_minus_short": ci(_jit(-0.04 if k != "human" else -0.12, 0.04, *key), 0.03, -1, 1)
    # hybrid workflow: the model screens, a human reads what it flags (its positive rate); classical TAR reads a larger slice; human-only reads all
    elif mid == "human_share": ci(1.0 if k == "human" else _jit(0.30 if k == "tar" else 0.16, 0.07, *key), 0.02)
    elif mid in ("latency_p50_ms", "hours_per_100k") and k == "tar" and ex != "workflow":
        return None  # classical TAR has no per-document model latency; its cost is the human review it drives
    elif mid == "latency_p50_ms": cell.update(v=round(_jit(c["latency"], c["latency"] * 0.2, *key), 1), lo=None, hi=None, n=200)
    elif mid == "usd_per_100k": cell.update(v=round(_jit(c["usd"], c["usd"] * 0.2, *key), 2), lo=None, hi=None, n=None)
    elif mid == "hours_per_100k":
        if ex == "workflow":  # human hours in the hybrid workflow: the share a human reads, at 55 docs/hour
            share = 1.0 if k == "human" else _jit(0.30 if k == "tar" else 0.16, 0.07, ds, ex, arm["id"], "human_share")
            v = max(0.0, share) * 1e5 / 55
        else:  # wall-clock hours of the arm itself
            v = (c["latency"] / 1000 * 1e5 / 3600) if k != "human" else 1e5 / 55
        cell.update(v=round(_jit(v, v * 0.15, *key), 1), lo=None, hi=None, n=None)
    else:
        return None
    if k == "human":
        cell["note"] = arm.get("note")
    return cell

# ------------------------------------------------------------------------------------------------ measured

def _ci(x: list[float] | None) -> dict[str, Any]:
    return dict(v=x[0], lo=x[1], hi=x[2]) if x else dict(v=None, lo=None, hi=None)

def _measured(findings: dict, ds: dict, ex: str, arm_id: str, mid: str) -> dict[str, Any] | None:
    recs = [r for r in findings["records"] if r["corpus"] == ds["findings"] and r["model"] == arm_id and r["arm"] == "multi" and not r["tag"]]
    if not recs:
        return None
    r = recs[0]; doc = r["all"]["doc"]
    if ex in ("accuracy", "bias"):
        if mid in ("recall", "precision", "elusion"):
            return dict(**_ci(doc.get(mid)), n=doc.get("n"), planned=False)
        if mid == "f1":
            return dict(v=doc.get("f1"), lo=None, hi=None, n=doc.get("n"), planned=False)
        if mid == "prevalence_ratio":
            tp, fp, fn = doc.get("tp", 0), doc.get("fp", 0), doc.get("fn", 0)
            return dict(v=round((tp + fp) / (tp + fn), 4), lo=None, hi=None, n=doc.get("n"), planned=False) if (tp + fn) else None
        return None  # recall_long_minus_short needs per-decision records
    if ex == "speed_cost":
        o = r["ops"]
        if mid == "latency_p50_ms":
            ci = o.get("doc_latency_p50_ci_ms")
            return dict(v=o.get("doc_latency_p50_ms"), lo=ci[0] if ci else None, hi=ci[1] if ci else None, n=None, planned=False)
        if mid == "usd_per_100k":
            c = o.get("cost_per_doc")
            return dict(v=None if c is None else round(c * 1e5, 2), lo=None, hi=None, n=None, planned=False)
        if mid == "hours_per_100k":
            return dict(v=o.get("hours_per_100k_docs"), lo=None, hi=None, n=None, planned=False)
    if ex == "consistency" and ds["id"] == "mnk":
        det = findings.get("determinism") or {}
        cells = [c for c in det.get("cells", []) if c["model"] == arm_id and c["arm"] == "multi" and c["setting"] == "default"]
        if not cells:
            return None
        c = cells[0]
        if mid in ("decision_flip", "doc_flip", "identical_prob") and c.get(mid):
            return dict(**_ci(c[mid]), n=c.get("n_decisions"), planned=False)
    return None

# ------------------------------------------------------------------------------------------------ export

def export_study(findings_path: Path, dest: Path) -> Path:
    findings = json.loads(findings_path.read_text())
    arms_by_id = {a["id"]: a for a in ARMS}
    datasets = []
    for d in DATASETS:
        d = dict(d)
        if d["findings"]:
            meta = findings["corpora"][d["findings"]]
            d.update(n_docs=meta["n_docs"], n_issues=meta["n_issues"], gold=meta["gold"])
        datasets.append(d)

    values: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    status: dict[str, dict[str, str]] = {}  # experiment -> dataset -> measured|planned|na
    for ex in EXPERIMENTS:
        status[ex["id"]] = {}
        for ds in datasets:
            if ds["id"] not in ex["datasets"]:
                status[ex["id"]][ds["id"]] = "na"
                continue
            any_measured = False
            for arm in ARMS:
                if arm["kind"] == "human" and arm["id"] not in ex["humans"]:
                    continue
                if arm["kind"] == "human" and arm["id"] == "human@firstpass" and ds["id"] not in LEGAL:
                    continue
                for m in ex["measures"]:
                    cell = None
                    if ds["status"] == "measured" and arm["status"] == "measured":
                        cell = _measured(findings, ds, ex["id"], arm["id"], m["id"])
                    if cell is None:
                        cell = _placeholder(ds["id"], ex["id"], arm, m["id"])
                    if cell is None or cell.get("v") is None:
                        continue
                    any_measured |= not cell["planned"]
                    values.setdefault(ds["id"], {}).setdefault(ex["id"], {}).setdefault(arm["id"], {})[m["id"]] = cell
            status[ex["id"]][ds["id"]] = "measured" if any_measured else "planned"

    out = dict(
        generated=date.today().isoformat(),
        datasets=datasets,
        arms=ARMS,
        experiments=[dict(e, status=status[e["id"]]) for e in EXPERIMENTS],
        values=values,
    )
    dest.write_text(json.dumps(out, indent=1))
    return dest

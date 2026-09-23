"""Markdown report generator: results/<corpus>/REPORT.md."""

from __future__ import annotations

import json
from pathlib import Path

from .metrics import agreement, macro_f1, op_metrics, pooled_metrics, question_metrics
from .runner import load_predictions, parse_job_stem
from .scope import in_scope
from .tasks import TaskSet, load_corpus


def _f(v, pct=False, nd=3):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{v*100:.1f}" if pct else f"{v:.{nd}f}"


def _rebind(preds, docs, ts):
    by = {d.id: d for d in docs}
    out = []
    for p in preds:
        d = by.get(p.doc_id)
        if d is None or p.question not in ts.questions:  # out-of-scope document or dropped question
            continue
        p.gold = d.gold(p.question, ts.negative_label); p.gray = p.question in d.gray
        out.append(p)
    return out


def collect(out: Path, corpus: str, arms: list[str], docs, ts, tags: tuple[str, ...] = ("",)) -> dict[str, list]:
    found = {}
    for a in arms:
        d = out / corpus / a
        if not d.exists():
            continue
        for f in sorted(d.glob("*.jsonl")):
            mk, tag = parse_job_stem(f.stem)
            if tag not in tags:
                continue
            preds = _rebind(load_predictions(f), docs, ts)
            preds = [p for p in preds if p.gold is not None]
            if preds:
                found[(mk, a, tag)] = preds
    return found


def md_table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def write_report(task: Path, data: Path, out: Path, corpus: str, arms=("single", "multi"), tags=("",), title: str | None = None) -> Path:
    ts = TaskSet.load(task)
    docs = in_scope(corpus, load_corpus(data))
    pos = ts.positive_label
    found = collect(out, corpus, list(arms), docs, ts, tags)
    n_docs = len(docs)
    n_pos = {q: sum(1 for d in docs if d.labels.get(q) == pos) for q in ts.qids}
    n_gray = {q: sum(1 for d in docs if q in d.gray) for q in ts.qids}

    L: list[str] = []
    L.append(f"# {title or corpus}: results\n")
    L.append(f"Corpus: `{data}` — {n_docs} documents × {len(ts.qids)} questions = {n_docs*len(ts.qids):,} decisions per model-arm.\n")
    L.append("Question | breadth | positives | gray")
    L.append("---|---|---|---")
    for q in ts.qids:
        qq = ts.questions[q]
        L.append(f"{q} ({qq.title}) | {qq.breadth or '—'} | {n_pos[q]} | {n_gray[q]}")
    L.append("")

    def key_label(k):
        mk, a, tag = k
        return f"{mk} [{a}]" + (f" #{tag}" if tag else "")

    for gray_mode, gtitle in [(False, "all gold labels"), (True, "gray-flagged decisions excluded")]:
        L.append(f"## Pooled results ({gtitle})\n")
        L.append("Micro-pooled over all (document, question) decisions at each model's own label. `bestF1@thr` re-thresholds `p_responsive`. `R@90 review%` = share of the population you would review to reach 90% recall ranking by `p_responsive`.\n")
        hdr = ["model [arm]", "n", "prec", "recall", "F1", "macro-F1", "elusion", "κ", "ROC-AUC", "PR-AUC", "Brier", "ECE", "bestF1@thr", "R@90 prec / review%", "R@95 review%"]
        rows = []
        for k in sorted(found, key=lambda k: (k[1], k[0])):
            preds = found[k]
            pm = pooled_metrics(preds, pos, gray_mode)
            qms = [question_metrics(q, preds, pos, gray_mode) for q in ts.qids]
            r90 = pm.recall_targets.get("recall@90"); r95 = pm.recall_targets.get("recall@95")
            rows.append([key_label(k), str(pm.n), _f(pm.precision, 1), _f(pm.recall, 1), _f(pm.f1, 1), _f(macro_f1(qms), 1), _f(pm.elusion, 1), _f(pm.kappa, nd=2),
                         _f(pm.roc_auc), _f(pm.pr_auc), _f(pm.brier), _f(pm.ece),
                         f"{_f(pm.best_f1,1)}@{_f(pm.best_f1_threshold, nd=2)}",
                         f"{_f(r90['precision'],1)} / {_f(r90['review_fraction'],1)}" if r90 else "—",
                         _f(r95["review_fraction"], 1) if r95 else "—"])
        L.append(md_table(hdr, rows)); L.append("")

    L.append("## Speed and cost\n")
    L.append("Latency is per API call as observed from the client (single arm = one question per call; multi arm = all questions per call, so per-decision cost is lower). `paid $` is what we were charged after batch/flex/cache discounts; `list $/1k` is standard-tier price per 1,000 decisions, the fair cross-vendor comparison.\n")
    hdr = ["model [arm]", "resolved model", "p50 ms", "p95 ms", "in tok/decision", "cached", "out tok", "paid $", "list $", "list $/1k decisions", "pricing", "label/prob inconsistent"]
    rows = []
    for k in sorted(found, key=lambda k: (k[1], k[0])):
        preds = found[k]; o = op_metrics(preds, pos)
        res = next((p.model_resolved for p in preds if not p.error), "")
        rows.append([key_label(k), res, _f(o.latency_p50_ms, nd=0), _f(o.latency_p95_ms, nd=0), f"{o.input_tokens_mean:,.0f}", f"{o.cached_tokens_mean:,.0f}", f"{o.output_tokens_mean:,.0f}",
                     f"{o.total_cost_usd:.2f}", f"{o.total_list_cost_usd:.2f}", f"{o.cost_per_1k_docs_usd:.3f}", ",".join(f"{m}:{n}" for m, n in o.pricing_modes.items()), _f(o.label_prob_inconsistent, 1) + "%"])
    L.append(md_table(hdr, rows)); L.append("")

    # per-question matrices
    for metric, name in [("recall", "Recall"), ("precision", "Precision"), ("f1", "F1"), ("roc_auc", "ROC-AUC")]:
        L.append(f"## Per-question {name} (all gold)\n")
        hdr = ["model [arm]"] + [q.replace("rfp", "").split("_")[0] if q.startswith("rfp") else q for q in ts.qids]
        rows = []
        for k in sorted(found, key=lambda k: (k[1], k[0])):
            preds = found[k]
            vals = []
            for q in ts.qids:
                m = question_metrics(q, preds, pos, False)
                v = getattr(m, metric)
                vals.append(_f(v, metric != "roc_auc", nd=3))
            rows.append([key_label(k)] + vals)
        L.append(md_table(hdr, rows)); L.append("")

    # Jev ablation table
    jev = {k: v for k, v in found.items() if k[0].startswith("jev@") and k[1] == "single"}
    if len(jev) > 1:
        L.append("## Jev ablations (single arm, all gold; Δ vs base)\n")
        base = jev.get(("jev@base", "single", ""))
        bm = pooled_metrics(base, pos, False) if base else None
        hdr = ["variant", "what changes", "prec", "recall", "F1", "ΔF1", "ROC-AUC", "PR-AUC", "Brier", "bestF1", "in tok", "p50 ms", "list $/1k"]
        from .providers.typesafe import VARIANTS
        desc = {"base": "Noul · RFP text · pos/neg criteria · structured state · with matter context", "choice": "Choice over the two labels", "score": "5-level Score, normalized", "crit_none": "no criteria (instructions only)",
                "crit_struct": "structured (JSON-like) criteria", "literal": "plain-language literal rewrite of the RFP", "no_context": "no matter background in state", "state_string": "state as one string, not a dict",
                "gate": "× relevance gate probability", "ensemble": "mean of 3 phrasings", "decompose": "OR over subpart questions (where defined)", "preview": "jev-preview model", "recipe": "chosen combination"}
        rows = []
        for k in sorted(jev, key=lambda k: list(VARIANTS).index(k[0][4:]) if k[0][4:] in VARIANTS else 99):
            preds = jev[k]; pm = pooled_metrics(preds, pos, False); o = op_metrics(preds, pos)
            d = (pm.f1 - bm.f1) * 100 if (bm and pm.f1 is not None and bm.f1 is not None) else None
            rows.append([k[0][4:], desc.get(k[0][4:], ""), _f(pm.precision, 1), _f(pm.recall, 1), _f(pm.f1, 1), (f"{d:+.1f}" if d is not None else "—"), _f(pm.roc_auc), _f(pm.pr_auc), _f(pm.brier), _f(pm.best_f1, 1),
                         f"{o.input_tokens_mean:,.0f}", _f(o.latency_p50_ms, nd=0), f"{o.cost_per_1k_docs_usd:.3f}"])
        L.append(md_table(hdr, rows)); L.append("")

    # agreement
    ks = sorted(found, key=lambda k: (k[1], k[0]))
    if 1 < len(ks) <= 16:
        L.append("## Inter-model agreement (Cohen's κ on labels)\n")
        hdr = [""] + [key_label(k)[:22] for k in ks]
        rows = [[key_label(a)[:22]] + [_f(agreement(found[a], found[b]), nd=2) for b in ks] for a in ks]
        L.append(md_table(hdr, rows)); L.append("")

    path = out / corpus / "REPORT.md"
    path.write_text("\n".join(L))
    return path

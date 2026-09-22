"""Export worked examples (real request payload + recorded output) for the site's "how it works" modal.

For every corpus, two documents are chosen for one question (one gold-positive, one gold-negative,
short enough to read). For each configuration the request is rebuilt with the same provider code
that ran the benchmark, and the output is the row actually recorded in results/. Nothing is
re-run and nothing is paid for.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import MODELS
from .providers.laya_ import LAYA_VARIANTS, LayaProvider
from .providers.lexical import _terms
from .providers.llm_common import SYSTEM_PROMPT, build_decision_model, build_prefix
from .providers.typesafe import SCORE_LEVELS, VARIANTS, JevConfig, TypeSafeProvider
from .runner import load_predictions
from .tasks import Document, TaskSet, load_corpus

CORPORA = [
    ("veridian", "tasks/veridian.yaml", "data/veridian/veridian.jsonl"),
    ("mnk", "tasks/mallinckrodt.yaml", "data/mallinckrodt/mnk.jsonl"),
    ("cuad", "tasks/cuad.yaml", "data/cuad/cuad.jsonl"),
    ("trec", "tasks/trec.yaml", "data/trec/eval.jsonl"),
]

MAX_DOC_CHARS = 2600

# Issues to show per corpus. Otherwise the pick is automatic (an issue with sub-questions, structured
# criteria and a literal phrasing, so every lever is visible). TREC's automatic pick was George W. Bush,
# which reads like a name search; faith-based initiatives is a conceptual issue.
PREFERRED_QUESTION = {"trec": "faith_based"}

JEV_NOTES: dict[str, str] = {
    "base": "The default. One Noul question per issue: a yes/no question whose answer is a probability. The RFP text is the instruction; the positive and negative descriptions from the task file are the true/false criteria. The state is a structured object with the matter background and the document.",
    "choice": "Same instruction and criteria, but asked as a Choice between the two labels rather than a yes/no Noul. The model returns a probability for each label and picks one; p(responsive) is what we score.",
    "score": "Asked as a Score on a five-point ordinal scale from 'clearly not responsive' to 'clearly responsive'. The criteria are folded into the instruction text. The scored probability is the level divided by four.",
    "crit_none": "The Noul question with no criteria at all: only the instruction. Tests how much the true/false descriptions are doing.",
    "crit_struct": "Criteria supplied as the structured object from the task file (what / includes / excludes / examples) instead of prose. Falls back to prose where a question has no structured block.",
    "literal": "Instruction replaced by the plain-language 'literal' phrasing from the task file (a reviewer's one-line version) instead of the verbatim RFP text.",
    "no_context": "The matter background is dropped from the state; the model sees only the document.",
    "state_string": "The state is a single flat string ('MATTER BACKGROUND: ... DOCUMENT: ...') instead of a structured object with named fields. This lever won the Veridian dev split and is the recipe.",
    "gate": "An extra Noul asks whether the document has anything to do with the matter at all. Each issue probability is multiplied by the gate probability.",
    "ensemble": "Three phrasings of the same question (RFP text, literal, title + positive description) are asked as three Nouls and their probabilities averaged.",
    "decompose": "Where the task file breaks an issue into atomic sub-questions, each is asked as its own Noul and the issue probability is the max across them (logical OR).",
    "preview": "Identical request to the default, sent to the jev-preview model instead of jev-1.13.0.",
}

LAYA_NOTES: dict[str, str] = {
    "base": "Same request shape as Jev's default, run through the local Laya encoder. Laya packs the question head into at most 192 tokens and the whole input into 512, so on these corpora the RFP instruction and criteria are silently truncated and most documents are cut from the right.",
    "choice": "Choice over the two labels instead of Noul.",
    "score": "Five-level Score with the criteria folded into the instruction.",
    "literal": "Instruction replaced by the shorter literal phrasing; fits more of the question into the 192-token head.",
    "gate": "An extra matter-relevance Noul gates each issue probability.",
    "ensemble": "Three phrasings averaged; each is truncated the same way.",
    "decompose": "Sub-questions asked separately and OR'd.",
    "compact": "A one-line instruction ('Is this document responsive to the request for production about: <title>?') and one-sentence criteria, sized to fit Laya's 192-token head so nothing in the question is truncated.",
    "chunk": "The document is split into overlapping windows sized to Laya's remaining context (about 300 tokens), each window is scored, and the per-question probability is the max over windows. Up to 16 windows.",
    "recipe": "compact + chunk: the two levers that address Laya's 512-token context. Neither changes what is being asked; both change how much of it Laya can actually read.",
    "recipe_choice": "compact + chunk with the Choice form.",
}

LLM_NOTE = (
    "One chat completion with a system prompt, a user message (matter background, the request block with "
    "responsive / not-responsive criteria, the document), and a JSON schema the vendor enforces on the output. "
    "The model returns a label and p_responsive; there is no free text. The prefix (everything before the "
    "document) is identical across documents so prompt caches can hit."
)


def _pick_examples(ts: TaskSet, docs: list[Document], results: Path, corpus: str) -> tuple[str, list[Document]]:
    """One question, two short documents (gold positive and gold negative) that most single-arm runs scored."""
    scored: dict[str, set[str]] = {}
    for f in (results / corpus / "single").glob("*.jsonl"):
        if "__latency" in f.name or "__rep" in f.name:
            continue
        for p in load_predictions(f):
            scored.setdefault(p.question, set()).add(p.doc_id)
    # prefer a question with literal + structured + subparts so every lever shows a visible difference
    def q_rank(qid: str) -> tuple:
        q = ts.questions[qid]
        return (bool(q.subparts), bool(q.structured), bool(q.literal), len(scored.get(qid, ())))
    order = sorted(ts.qids, key=q_rank, reverse=True)
    if corpus in PREFERRED_QUESTION:
        order = [PREFERRED_QUESTION[corpus]] + [q for q in order if q != PREFERRED_QUESTION[corpus]]
    for qid in order:
        ok = scored.get(qid, set())
        short = [d for d in docs if len(d.text) <= MAX_DOC_CHARS and d.id in ok and qid not in d.gray]
        pos = [d for d in short if d.gold(qid, ts.negative_label) == ts.positive_label]
        neg = [d for d in short if d.gold(qid, ts.negative_label) == ts.negative_label]
        if pos and neg:
            pos.sort(key=lambda d: -len(d.text))
            neg.sort(key=lambda d: -len(d.text))
            return qid, [pos[0], neg[0]]
    qid = ts.qids[0]
    return qid, docs[:2]


def _output(results: Path, corpus: str, model_file: str, doc_id: str, qid: str) -> dict | None:
    for arm in ("single", "multi"):
        f = results / corpus / arm / f"{model_file}.jsonl"
        if not f.exists():
            continue
        for p in load_predictions(f):
            if p.doc_id == doc_id and p.question == qid:
                d = asdict(p)
                return {
                    "arm": arm,
                    "label": d["label"], "p_positive": d["p_positive"], "confidence": d["confidence"],
                    "latency_ms": d["latency_ms"], "input_tokens": d["input_tokens"], "output_tokens": d["output_tokens"],
                    "cost_usd": d["cost_usd"], "model_resolved": d["model_resolved"], "raw": d.get("raw") or {},
                    "gold": d["gold"], "error": d["error"],
                }
    return None


def _cfg_dict(cfg: JevConfig) -> dict:
    return asdict(cfg)


def _jev_request(ts: TaskSet, qid: str, doc: Document, cfg: JevConfig) -> dict:
    prov = TypeSafeProvider.__new__(TypeSafeProvider)
    prov.cfg = cfg
    questions, plan = prov._questions(ts, [qid])
    return {
        "model": cfg.model_id,
        "state": prov._state(ts, doc),
        "questions": {k: v.model_dump(exclude_none=True) for k, v in questions.items()},
        "aggregate": _aggregate_note(cfg, plan[qid]),
    }


def _laya_request(ts: TaskSet, qid: str, doc: Document, cfg: JevConfig) -> dict:
    prov = LayaProvider.__new__(LayaProvider)
    prov.cfg = cfg
    questions, plan = prov._questions(ts, [qid])
    st = prov._state(ts, doc.text)
    return {
        "state": st,
        "questions": questions,
        "windows": "document split into <=16 overlapping ~300-token windows; p = max over windows" if cfg.chunk else "whole document (truncated from the right at the 512-token cap)",
        "aggregate": _aggregate_note(cfg, plan[qid]),
    }


def _aggregate_note(cfg: JevConfig, keys: list[tuple[str, str]]) -> str:
    if cfg.decompose and len(keys) > 1:
        s = f"p = max over {len(keys)} sub-questions"
    elif cfg.ensemble:
        s = f"p = mean over {len(keys)} phrasings"
    elif cfg.form == "choice":
        s = "p = probabilities['responsive']; label = the chosen option"
    elif cfg.form == "score":
        s = f"p = score / {len(SCORE_LEVELS) - 1}"
    else:
        s = "p = noul"
    if cfg.gate:
        s += "; then p = p × p(gate)"
    return s + "; label = responsive if p ≥ 0.5"


def _llm_request(ts: TaskSet, qid: str, doc: Document) -> dict:
    schema = build_decision_model(ts, [qid]).model_json_schema()
    return {
        "system": SYSTEM_PROMPT,
        "user_prefix": build_prefix(ts, [qid]),
        "user_suffix": f'<document id="{doc.id}">\n{doc.text}\n</document>',
        "response_schema": schema,
    }


def _lexical_request(ts: TaskSet, qid: str, doc: Document) -> dict:
    terms = sorted(_terms(ts.questions[qid], ts))
    return {"terms": terms, "rule": "score saturates with the number of distinct terms present (~3 hits → 0.5, ~8 → 0.9); label = responsive if score ≥ 0.5"}


TAR_WORKFLOW = {
    "t1": [
        "Draw a random sample of N documents from the collection.",
        "A reviewer reads each and codes it for every issue (simulated here from the gold labels; 50 documents/hour, $65/hour).",
        "Fit TF-IDF (word 1-2 grams, sublinear tf) and balanced logistic regression: one model for any-issue relevance and one per issue with at least 5 coded positives.",
        "Choose each model's cutoff by 5-fold cross-validation on the coded sample only: the score that keeps 80% of the sample's positives (or, in the F1 variant, the score that maximises F1).",
        "Score the rest of the collection. A document is produced on an issue when it clears the relevance cutoff and that issue's cutoff; the coded documents keep the reviewer's codes.",
    ],
    "t1_div": [
        "Draw a diversity sample of N documents from the collection: reduce the collection's TF-IDF matrix to 100 dimensions with a truncated SVD (fit on at most 50,000 documents, every document projected, rows L2-normalised), cluster it into N groups with k-means (MiniBatchKMeans), and take the document nearest each cluster centre (one per cluster; any empty cluster is filled by a random draw).",
        "A reviewer reads each and codes it for every issue (simulated here from the gold labels; 50 documents/hour, $65/hour).",
        "Fit TF-IDF (word 1-2 grams, sublinear tf) and balanced logistic regression: one model for any-issue relevance and one per issue with at least 5 coded positives.",
        "Choose each model's cutoff by 5-fold cross-validation on the coded sample only: the score that keeps 80% of the sample's positives. The coded sample is not a random sample of the collection, so that recall estimate is a guide rather than an unbiased one.",
        "Score the rest of the collection. A document is produced on an issue when it clears the relevance cutoff and that issue's cutoff; the coded documents keep the reviewer's codes.",
    ],
    "cal": [
        "Control set: the reviewer codes a simple random sample of the collection first (10% of the pool, capped at 500 and sized for at least ~30 relevant documents; a fixed 2,000 on TREC's 286k collection). These documents never enter the review queue and are not trained on; their coding counts as review effort and their codes are part of the production set.",
        "Seed: random documents plus the same number of the strongest keyword-floor hits, coded by the reviewer (50 + 50 on the 800-document Mallinckrodt pool, 100 + 100 elsewhere).",
        "Fit TF-IDF + balanced logistic regression on everything queued and coded so far for any-issue relevance.",
        "Rank the collection; the reviewer codes the top uncoded batch (50 / 100 / 1,000 documents by collection size), tagging issues as they go.",
        "Estimate recall from the control set: whenever a batch is picked, every control document scoring at or above the batch's lowest queued score counts as reached from then on (it would have been in the batch had it not been held out); recall is the share of control-set documents coded relevant that have been reached. Repeat 3-5 and stop once the estimate is at or above the target (80%; 75% in the 'cal_75' variant) for two consecutive batches, or when the pool is exhausted. (The 'knee stop' variant uses Cormack & Grossman's knee method and no control set.)",
        "The production set is everything the reviewer coded relevant, control set included; that is what the site plots, scored against gold on the pool CAL ran over. The review set (everything read), the recall estimate at stop against the true figure, and the classifier applied on its own to the evaluation set at the control-set cutoff are reported alongside.",
    ],
}


def _tar_request(side: dict) -> dict:
    spec = side["spec"]; med = side["median"]
    workflow = TAR_WORKFLOW["t1_div" if spec["kind"] == "t1" and spec.get("sampling") == "diversity" else spec["kind"]]
    req = {"workflow": workflow, "reviewer": {"docs_per_hour": side["reviewer"]["docs_per_hour"], "usd_per_hour": side["reviewer"]["usd_per_hour"],
                                                              "miscode_rate": side["reviewer"]["miscode_rate"]},
           "classifier": {"features": "tf-idf, word 1-2 grams, min_df 2, sublinear tf, ≤300k features", "model": "logistic regression, liblinear, class_weight balanced, C=1"}}
    if spec["kind"] == "t1":
        req["training_sample"] = {"sampling": spec.get("sampling", "random"), "documents_coded": med["docs_reviewed"], "positives_any_issue": med["train_positives_any"], "issues_with_own_model": med["issue_models"],
                                  "cutoff_rule": "80% recall (5-fold CV on the sample)" if spec["rule"] == "recall80" else "max F1 (5-fold CV on the sample)"}
        if spec.get("sampling") == "diversity":
            req["training_sample"]["diversity"] = {"svd_dims": med.get("svd_dims"), "svd_fit_rows": med.get("svd_fit_rows"), "clusters": med.get("k"), "empty_clusters": med.get("empty_clusters")}
    else:
        ctrl = med.get("control_set") or {}
        req["review"] = {"documents_coded": med["docs_reviewed"], "control_set": ctrl.get("n", 0), "queued": med.get("docs_queued"),
                         "batch": med["batch"], "batches": med["batches"], "recall_target": med.get("target"), "stop": med["stop"],
                         "estimated_recall_at_stop": med.get("est_recall_at_stop"), "relevant_reached": med.get("found_gold"), "relevant_in_pool": med.get("relevant_in_pool"),
                         "review_set_precision": med.get("review_set_precision"), "plotted": med.get("plotted", "production set on pool"),
                         "pool": f"{side['n_corpus']:,} documents, {med.get('pool_richness', 0):.0%} relevant" + (" (downsampled from the 61%-rich benchmark sample)" if med.get("pool_ids") else "")}
        if med.get("classifier"):
            cl = med["classifier"]
            req["classifier_alone"] = {"cutoff": "score reaching the recall target on the control set",
                                       "eval_set": {k: cl["eval"].get(k) for k in ("recall", "precision", "flagged", "relevant", "n")}}
    req["effort"] = {"hours": round(med["hours"], 1), "usd": round(med["cost_usd"]), "share_of_collection": round(med["docs_reviewed"] / side["n_corpus"], 3)}
    return req


def _template(obj, doc_text: str, context: str):
    """Replace the document text and matter context with placeholders so the payload stays small."""
    if isinstance(obj, str):
        if doc_text and doc_text in obj:
            obj = obj.replace(doc_text, "{{document}}")
        if context and context in obj:
            obj = obj.replace(context, "{{context}}")
        return obj
    if isinstance(obj, dict):
        return {k: _template(v, doc_text, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_template(v, doc_text, context) for v in obj]
    return obj


def export(out: Path = Path("results"), dest: Path = Path("results/examples.json")) -> dict:
    payload: dict = {"corpora": {}, "notes": {"jev": JEV_NOTES, "laya": LAYA_NOTES, "llm": LLM_NOTE}, "score_levels": SCORE_LEVELS}
    for corpus, task_path, data_path in CORPORA:
        ts = TaskSet.load(task_path)
        docs = load_corpus(data_path)
        qid, ex_docs = _pick_examples(ts, docs, out, corpus)
        q = ts.questions[qid]
        c: dict = {
            "context": ts.context,
            "question": {"id": qid, "title": q.title, "rfp_text": q.rfp_text},
            "documents": [{"id": d.id, "text": d.text, "gold": d.gold(qid, ts.negative_label)} for d in ex_docs],
            "configs": {},
        }
        # Jev variants
        for name, cfg in VARIANTS.items():
            if name == "recipe":
                continue
            key = f"jev@{name}"
            c["configs"][key] = {
                "group": "jev", "variant": name, "settings": _cfg_dict(cfg),
                "examples": [
                    {"request": _jev_request(ts, qid, d, cfg), "output": _output(out, corpus, f"jev__{name}", d.id, qid)}
                    for d in ex_docs
                ],
            }
        # Laya variants for each checkpoint present
        for ck in ("laya", "laya-typed", "laya-multilingual"):
            for name, cfg in LAYA_VARIANTS.items():
                key = f"{ck}@{name}"
                exs = [
                    {"request": _laya_request(ts, qid, d, cfg), "output": _output(out, corpus, f"{ck}__{name}", d.id, qid)}
                    for d in ex_docs
                ]
                if all(e["output"] is None for e in exs):
                    continue
                c["configs"][key] = {"group": ck, "variant": name, "settings": _cfg_dict(cfg), "examples": exs}
        # fine-tuned Laya
        for ck in (f"laya-ft-{corpus}",):
            for name in ("recipe", "compact", "base"):
                exs = [
                    {"request": _laya_request(ts, qid, d, LAYA_VARIANTS[name]), "output": _output(out, corpus, f"{ck}__{name}", d.id, qid)}
                    for d in ex_docs
                ]
                if any(e["output"] is not None for e in exs):
                    c["configs"]["laya-ft"] = {"group": "laya-ft", "variant": name, "settings": _cfg_dict(LAYA_VARIANTS[name]), "examples": exs}
                    break
        # LLMs + Gemma
        for mk in ("claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemma3-12b"):
            spec = MODELS[mk]
            exs = [{"request": _llm_request(ts, qid, d), "output": _output(out, corpus, mk, d.id, qid)} for d in ex_docs]
            c["configs"][mk] = {
                "group": "llm", "variant": mk,
                "settings": {"model_id": spec.model_id, "effort": spec.effort, "provider": spec.provider, **{k: v for k, v in spec.extra.items() if k in ("temperature", "num_ctx", "thinking")}, "structured_output": "json_schema"},
                "examples": exs,
            }
        exs = [{"request": _lexical_request(ts, qid, d), "output": _output(out, corpus, "lexical", d.id, qid)} for d in ex_docs]
        c["configs"]["lexical"] = {"group": "lexical", "variant": "lexical", "settings": {"threshold": 0.5}, "examples": exs}
        # classical TAR (no API: the request is the workflow and the coded sample; the output is the median seed's call)
        for side_path in sorted((out / corpus / "multi").glob("tar__*.tar.json")):
            side = json.loads(side_path.read_text()); name = side["variant"]
            exs = [{"request": _tar_request(side), "output": _output(out, corpus, f"tar__{name}", d.id, qid)} for d in ex_docs]
            if any(e["output"] is not None for e in exs):
                c["configs"][f"tar@{name}"] = {"group": "tar", "variant": name, "settings": {"seeds": len(side["seeds"]), "median_seed": side["median_seed"], "miscode_rate": side["spec"]["noise"], **({"sampling": side["spec"]["sampling"]} if side["spec"].get("sampling") else {})}, "examples": exs}
        for cfg in c["configs"].values():
            for i, ex in enumerate(cfg["examples"]):
                ex["request"] = _template(ex["request"], ex_docs[i].text, ts.context)
        payload["corpora"][corpus] = c
    dest.write_text(json.dumps(payload, ensure_ascii=False))
    return payload

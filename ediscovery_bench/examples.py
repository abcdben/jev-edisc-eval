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
    for qid in sorted(ts.qids, key=q_rank, reverse=True):
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
        for cfg in c["configs"].values():
            for i, ex in enumerate(cfg["examples"]):
                ex["request"] = _template(ex["request"], ex_docs[i].text, ts.context)
        payload["corpora"][corpus] = c
    dest.write_text(json.dumps(payload, ensure_ascii=False))
    return payload

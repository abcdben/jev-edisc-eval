"""Shared prompts + structured-output schemas for the generative LLMs.

Two arms:
- single: one question per call. Output {label, p_responsive}.
- multi: all questions per call. Output {<qid>: {label, p_responsive}, ...}.

The prompt is split into a *prefix* (system + matter context + the request
text(s)) that is identical across documents, so vendors' prompt caches can hit,
and a *suffix* carrying the document.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, create_model

from ..tasks import Document, Question, TaskSet

SYSTEM_PROMPT = (
    "You are a document review classifier working on an eDiscovery matter. Read the matter background, "
    "the request(s) for production, and the document. Decide whether the document is responsive to each "
    "request, and give a calibrated probability. Return only the structured result. Do not explain."
)

PhraseMode = Literal["rfp", "literal"]


def question_block(ts: TaskSet, q: Question, phrasing: PhraseMode = "rfp") -> str:
    text = q.literal if (phrasing == "literal" and q.literal) else q.rfp_text
    lab = ts.labels_for(q)
    return (
        f"<request id=\"{q.id}\" title=\"{q.title}\">\n{text}\n"
        f"<responsive_means>{lab[ts.positive_label]}</responsive_means>\n"
        f"<not_responsive_means>{lab[ts.negative_label]}</not_responsive_means>\n</request>"
    )


def build_prefix(ts: TaskSet, qids: list[str], phrasing: PhraseMode = "rfp") -> str:
    parts = []
    if ts.context:
        parts.append(f"<matter_background>\n{ts.context}\n</matter_background>")
    parts.append("\n\n".join(question_block(ts, ts.questions[q], phrasing) for q in qids))
    if len(qids) == 1:
        parts.append(
            "Classify the document as responsive or not_responsive to the request above, and give "
            "p_responsive, your probability from 0 to 1 that the document is responsive."
        )
    else:
        parts.append(
            "For EACH request above, classify the document as responsive or not_responsive and give "
            "p_responsive, your probability from 0 to 1 that the document is responsive to that request. "
            "Judge each request independently."
        )
    return "\n\n".join(parts)


def build_doc_suffix(doc: Document) -> str:
    return f"<document id=\"{doc.id}\">\n{doc.text}\n</document>"


def build_user_prompt(ts: TaskSet, qids: list[str], doc: Document, phrasing: PhraseMode = "rfp") -> str:
    return build_prefix(ts, qids, phrasing) + "\n\n" + build_doc_suffix(doc)


_model_cache: dict[tuple, type[BaseModel]] = {}


def build_decision_model(ts: TaskSet, qids: list[str]) -> type[BaseModel]:
    key = (ts.name, ts.positive_label, ts.negative_label, tuple(qids))
    if key in _model_cache:
        return _model_cache[key]
    label_type = Literal[(ts.positive_label, ts.negative_label)]  # type: ignore[valid-type]
    One = create_model(
        "Decision",
        label=(label_type, Field(description="responsive or not_responsive")),
        p_responsive=(float, Field(ge=0.0, le=1.0, description="Probability (0-1) that the document is responsive")),
    )
    if len(qids) == 1:
        M = One
    else:
        fields = {qid: (One, Field(description=f"Decision for request {qid}")) for qid in qids}
        M = create_model("Decisions", **fields)  # type: ignore[call-overload]
    _model_cache[key] = M
    return M


def parse_decisions(obj: BaseModel, qids: list[str]) -> tuple[dict[str, float], dict[str, str]]:
    probs: dict[str, float] = {}
    labels: dict[str, str] = {}
    if len(qids) == 1:
        probs[qids[0]] = float(getattr(obj, "p_responsive"))
        labels[qids[0]] = str(getattr(obj, "label"))
    else:
        for qid in qids:
            one = getattr(obj, qid)
            probs[qid] = float(getattr(one, "p_responsive"))
            labels[qid] = str(getattr(one, "label"))
    return probs, labels

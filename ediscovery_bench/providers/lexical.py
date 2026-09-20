"""Lexical baseline: no model, no gold peeking.

For each question, content terms are pulled from the request text, the
positive description, and the structured `includes`/`examples` lists. A
document's score is a saturating function of how many distinct terms it
contains. This is the "is the set just keyword matching?" control: if it
scores close to the System 1 / LLM models, the corpus is too easy.
"""

from __future__ import annotations

import math
import re

from ..tasks import Document, Question, TaskSet
from .base import Provider, RawResult

STOP = set(
    """
    a an the and or of to in on for with by from at as is are was were be been being this that these those
    it its into about any all such other than which who whom whose what when where whether including include
    includes concerning regarding relating related documents document communications communication between
    veridian mallinckrodt company product products request production responsive not answer yes no only if
    also both each either every made make making more most much may might must need needs new non one per
    same several shall should since some still their them then there they thing things through under until
    upon use used using very via well whether while will within without would your you our we us can could
    """.split()
)


def _terms(q: Question, ts: TaskSet) -> set[str]:
    text = " ".join([q.rfp_text, q.positive_desc])
    if q.structured:
        r = q.structured.get(ts.positive_label) or {}
        for k in ("what", "includes", "examples"):
            v = r.get(k)
            if isinstance(v, list):
                text += " " + " ".join(str(x) for x in v)
            elif v:
                text += " " + str(v)
    toks = re.findall(r"[a-z][a-z0-9\-]{3,}", text.lower())
    return {t for t in toks if t not in STOP and not t.isdigit()}


class LexicalProvider(Provider):
    def __init__(self, spec):
        super().__init__(spec)
        self._cache: dict[tuple[str, str], set[str]] = {}

    def _q_terms(self, ts: TaskSet, qid: str) -> set[str]:
        k = (ts.name, qid)
        if k not in self._cache:
            self._cache[k] = _terms(ts.questions[qid], ts)
        return self._cache[k]

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        doc_toks = set(re.findall(r"[a-z][a-z0-9\-]{3,}", doc.text.lower()))
        probs: dict[str, float] = {}
        raw: dict = {}
        for qid in qids:
            terms = self._q_terms(ts, qid)
            hits = len(terms & doc_toks)
            frac = hits / max(1, len(terms))
            # saturating: ~3 distinct hits -> 0.5, ~8 -> 0.9; scaled a bit by coverage
            p = 1.0 - math.exp(-(hits / 4.0) - 2.0 * frac)
            probs[qid] = float(min(0.999, max(0.001, p)))
            raw[f"{qid}_hits"] = hits
        return RawResult(
            p_positive=probs,
            labels={q: None for q in qids},
            confidence={q: None for q in qids},
            resolved_model="lexical-terms",
            input_tokens=len(doc.text) // 4,
            output_tokens=0,
            raw=raw,
        )

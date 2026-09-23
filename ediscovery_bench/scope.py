"""Study scope applied at scoring/export time, without touching the saved corpora or predictions.

TREC 2016, topic 404 "Eminent domain" (question id `eminent_domain`) was dropped from the study on
2026-09-23: NIST's three alternate assessors agreed with the primary assessor on only 7-28% of their
re-judged sample for that topic, and their precision against the primary's positives was 4-9%
(design/trec/dropped_eminent_domain.yaml, design/trec/calibration.md "Dropped topic"). The question
block moved out of tasks/trec.yaml, so every scorer that keys on the task set ignores its predictions.

The eval sample (data/trec/eval.jsonl) was drawn with a `pos:eminent_domain` stratum: 100 emails that
entered the sample only because they are gold-positive for 404. They would act as unintended extra
hard negatives for the other topics, so they are excluded here. eval.jsonl itself is not rebuilt
(that would reshuffle the seeded draws); the exclusion is a filter on `meta.stratum`. Documents in the
`hard_neg` and `random` strata that carry an `eminent_domain` label simply lose that label.
"""

from __future__ import annotations

from .tasks import Document

DROPPED_STRATA: dict[str, frozenset[str]] = {"trec": frozenset({"pos:eminent_domain"})}


def in_scope(corpus: str, docs: list[Document]) -> list[Document]:
    """Documents of `corpus` that are scored: drops the strata listed in DROPPED_STRATA."""
    drop = DROPPED_STRATA.get(corpus)
    if not drop:
        return list(docs)
    return [d for d in docs if d.meta.get("stratum") not in drop]


def scored_questions(preds, ts):
    """Predictions for questions in the task set only (a dropped question's rows are ignored everywhere)."""
    qs = ts.questions
    return [p for p in preds if p.question in qs]

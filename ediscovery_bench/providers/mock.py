"""Deterministic keyword classifier so the pipeline can be tested offline."""

from __future__ import annotations

import asyncio
import hashlib
import re

from ..tasks import Document, TaskSet
from .base import Provider, RawResult


class MockProvider(Provider):
    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        await asyncio.sleep(0.002)
        text = doc.text.lower()
        probs, labels = {}, {}
        for qid in qids:
            q = ts.questions[qid]
            words = {w for w in re.findall(r"[a-z]{6,}", q.positive_desc.lower())}
            hits = sum(1 for w in words if w in text)
            h = int(hashlib.md5((doc.id + qid).encode()).hexdigest(), 16) % 100 / 400
            p = min(0.99, 0.1 + 0.15 * hits + h)
            probs[qid] = p
            labels[qid] = None
        return RawResult(
            p_positive=probs, labels=labels, confidence={q: None for q in qids},
            resolved_model=self.spec.model_id, input_tokens=len(doc.text) // 4, output_tokens=12 * len(qids),
        )

"""Deterministic keyword classifier so the pipeline can be tested offline."""

from __future__ import annotations

import asyncio
import hashlib
import re

from ..tasks import Document, Task
from .base import Provider


class MockProvider(Provider):
    async def _classify(self, task: Task, doc: Document):
        await asyncio.sleep(0.005)
        text = doc.text.lower()
        scores: dict[str, float] = {}
        for name, desc in task.labels.items():
            words = {w for w in re.findall(r"[a-z]{5,}", (desc or "").lower())}
            hits = sum(1 for w in words if w in text)
            scores[name] = 1.0 + hits
        # add a stable pseudo-random nudge so probabilities aren't all ties
        h = int(hashlib.md5(doc.id.encode()).hexdigest(), 16) % 100 / 100
        first = task.label_names[0]
        scores[first] += h
        total = sum(scores.values())
        probs = {k: v / total for k, v in scores.items()}
        in_tok = max(1, len(doc.text) // 4)
        return probs, None, None, self.spec.model_id, in_tok, 12, {}

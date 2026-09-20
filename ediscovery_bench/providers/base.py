from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

from ..config import ModelSpec
from ..tasks import Document, Task


@dataclass
class Prediction:
    doc_id: str
    model_key: str
    model_resolved: str  # what the API said actually answered (e.g. jev-1.13.0)
    label: str
    probabilities: dict[str, float]  # over task labels, sums to ~1
    confidence: float | None  # provider-reported, if any (Jev Choice); else None
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    gold: str | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row: dict) -> "Prediction":
        return Prediction(**row)


class Provider(ABC):
    def __init__(self, spec: ModelSpec):
        self.spec = spec

    @abstractmethod
    async def _classify(self, task: Task, doc: Document) -> tuple[dict[str, float], str | None, float | None, str, int, int, dict]:
        """Return (probabilities, label_or_None, confidence, resolved_model, in_tok, out_tok, raw).

        If label is None the argmax of probabilities is used.
        """

    async def classify(self, task: Task, doc: Document) -> Prediction:
        t0 = time.perf_counter()
        try:
            probs, label, conf, resolved, in_tok, out_tok, raw = await self._classify(task, doc)
            latency = (time.perf_counter() - t0) * 1000
            probs = normalize(probs, task.label_names)
            if label is None or label not in task.labels:
                label = max(probs, key=probs.get)
            return Prediction(
                doc_id=doc.id,
                model_key=self.spec.key,
                model_resolved=resolved,
                label=label,
                probabilities=probs,
                confidence=conf,
                latency_ms=latency,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=self.spec.cost_usd(in_tok, out_tok),
                gold=doc.label,
                raw=raw,
            )
        except Exception as e:  # noqa: BLE001 - we want every failure recorded, not raised
            latency = (time.perf_counter() - t0) * 1000
            return Prediction(
                doc_id=doc.id,
                model_key=self.spec.key,
                model_resolved=self.spec.model_id,
                label="",
                probabilities={},
                confidence=None,
                latency_ms=latency,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                gold=doc.label,
                error=f"{type(e).__name__}: {e}",
            )

    async def healthcheck(self) -> str:
        """Cheap call proving auth + connectivity. Returns a one-line status."""
        from ..tasks import Task

        task = Task(
            name="healthcheck",
            kind="binary",
            labels={"yes": "The text mentions an invoice.", "no": "It does not."},
            instructions="Does this text mention an invoice?",
            positive_label="yes",
        )
        doc = Document(id="hc", text="Attached is invoice #4471 for the March services.")
        pred = await self.classify(task, doc)
        if pred.error:
            raise RuntimeError(pred.error)
        return (
            f"ok  model={pred.model_resolved}  label={pred.label}  "
            f"p(yes)={pred.probabilities.get('yes', 0):.2f}  {pred.latency_ms:.0f}ms  "
            f"tokens={pred.input_tokens}/{pred.output_tokens}  ${pred.cost_usd:.6f}"
        )

    async def aclose(self) -> None:
        return None


def normalize(probs: dict[str, float], labels: list[str]) -> dict[str, float]:
    """Clamp to [0,1], fill missing labels with 0, renormalize to sum 1."""
    out = {l: max(0.0, float(probs.get(l, 0.0) or 0.0)) for l in labels}
    s = sum(out.values())
    if s <= 0:
        return {l: 1.0 / len(labels) for l in labels}
    return {l: v / s for l, v in out.items()}

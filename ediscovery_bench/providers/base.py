from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

from ..config import ModelSpec
from ..tasks import Document, TaskSet


@dataclass
class Prediction:
    doc_id: str
    question: str
    model_key: str  # roster key, or jev variant key like "jev@choice"
    model_resolved: str  # what the API said actually answered
    arm: str  # "single" | "multi"
    label: str
    p_positive: float
    confidence: float | None
    latency_ms: float | None  # None for batch-mode rows
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cost_usd: float  # what we actually paid (flex/batch/cache discounts applied)
    list_cost_usd: float  # standard-tier price for the same tokens
    pricing_mode: str  # "standard" | "flex" | "batch"
    gold: str | None = None
    gray: bool = False
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row: dict) -> "Prediction":
        return Prediction(**row)


@dataclass
class RawResult:
    """What a provider returns for one API call covering one or more questions."""

    p_positive: dict[str, float]  # qid -> p(responsive)
    labels: dict[str, str | None]  # qid -> label or None (use threshold on p)
    confidence: dict[str, float | None]
    resolved_model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    pricing_mode: str = "standard"
    raw: dict[str, Any] = field(default_factory=dict)


class Provider(ABC):
    arm_supports_multi = True

    def __init__(self, spec: ModelSpec):
        self.spec = spec

    @property
    def key(self) -> str:
        return self.spec.key

    @abstractmethod
    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        """Answer `qids` (one for the single arm, all for the multi arm) about `doc`."""

    def cost(self, r: RawResult) -> tuple[float, float]:
        """(paid, list) cost. Providers override to apply cache/flex/batch pricing."""
        list_cost = self.spec.cost_usd(r.input_tokens, r.output_tokens)
        return list_cost, list_cost

    async def classify(self, ts: TaskSet, qids: list[str], doc: Document, arm: str) -> list[Prediction]:
        t0 = time.perf_counter()
        try:
            r = await self._call(ts, qids, doc)
            latency = (time.perf_counter() - t0) * 1000
            paid, listed = self.cost(r)
            # Split shared call cost evenly across questions so per-question sums are exact.
            n = len(qids)
            out = []
            for qid in qids:
                p = float(min(1.0, max(0.0, r.p_positive.get(qid, 0.5))))
                label = r.labels.get(qid)
                if label not in (ts.positive_label, ts.negative_label):
                    label = ts.positive_label if p >= 0.5 else ts.negative_label
                out.append(
                    Prediction(
                        doc_id=doc.id,
                        question=qid,
                        model_key=self.key,
                        model_resolved=r.resolved_model,
                        arm=arm,
                        label=label,
                        p_positive=p,
                        confidence=r.confidence.get(qid),
                        latency_ms=latency,
                        input_tokens=r.input_tokens // n,
                        output_tokens=r.output_tokens // n,
                        cached_tokens=r.cached_tokens // n,
                        cost_usd=paid / n,
                        list_cost_usd=listed / n,
                        pricing_mode=r.pricing_mode,
                        gold=doc.gold(qid, ts.negative_label),
                        gray=qid in doc.gray,
                        raw=r.raw if n == 1 else {},
                    )
                )
            return out
        except Exception as e:  # noqa: BLE001
            latency = (time.perf_counter() - t0) * 1000
            return [
                Prediction(
                    doc_id=doc.id,
                    question=qid,
                    model_key=self.key,
                    model_resolved=self.spec.model_id,
                    arm=arm,
                    label="",
                    p_positive=float("nan"),
                    confidence=None,
                    latency_ms=latency,
                    input_tokens=0,
                    output_tokens=0,
                    cached_tokens=0,
                    cost_usd=0.0,
                    list_cost_usd=0.0,
                    pricing_mode="standard",
                    gold=doc.gold(qid, ts.negative_label),
                    gray=qid in doc.gray,
                    error=f"{type(e).__name__}: {str(e)[:500]}",
                )
                for qid in qids
            ]

    async def healthcheck(self) -> str:
        from ..tasks import Question, TaskSet

        ts = TaskSet(
            name="healthcheck",
            context="A small company's mailbox.",
            questions={
                "invoice": Question(
                    id="invoice",
                    title="invoice",
                    rfp_text="All documents mentioning an invoice.",
                    positive_desc="The text mentions an invoice.",
                    negative_desc="It does not mention an invoice.",
                    literal="Does this text mention an invoice?",
                )
            },
        )
        doc = Document(id="hc", text="Attached is invoice #4471 for the March services.")
        preds = await self.classify(ts, ["invoice"], doc, arm="single")
        p = preds[0]
        if p.error:
            raise RuntimeError(p.error)
        return (
            f"ok  model={p.model_resolved}  label={p.label}  p={p.p_positive:.2f}  "
            f"{p.latency_ms:.0f}ms  tokens={p.input_tokens}/{p.output_tokens}  ${p.cost_usd:.6f} ({p.pricing_mode})"
        )

    async def aclose(self) -> None:
        return None

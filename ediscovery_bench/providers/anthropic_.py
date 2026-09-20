from __future__ import annotations

import asyncio
import json
import time

import anthropic

from ..tasks import Document, TaskSet
from .base import Provider, RawResult
from .llm_common import SYSTEM_PROMPT, build_decision_model, build_doc_suffix, build_prefix, parse_decisions

CACHE_READ_MULT = 0.10
CACHE_WRITE_MULT = 1.25
BATCH_MULT = 0.50


class AnthropicProvider(Provider):
    supports_batch = True

    def __init__(self, spec, phrasing: str = "rfp", batch: bool = False):
        super().__init__(spec)
        self.client = anthropic.AsyncAnthropic(max_retries=5, timeout=180.0)
        self.phrasing = phrasing
        self.batch = batch

    def _kwargs(self, ts: TaskSet, qids: list[str], doc: Document) -> dict:
        Decision = build_decision_model(ts, qids)
        schema = Decision.model_json_schema()
        thinking_on = self.spec.extra.get("thinking", {}).get("type") != "disabled"
        base_max = 2048 if len(qids) > 1 else 512
        kwargs: dict = dict(
            model=self.spec.model_id,
            # thinking tokens count against max_tokens; leave headroom when thinking may be on
            max_tokens=base_max + (12000 if thinking_on else 0),
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        # shared prefix, cacheable
                        {"type": "text", "text": build_prefix(ts, qids, self.phrasing), "cache_control": {"type": "ephemeral"}},
                        {"type": "text", "text": build_doc_suffix(doc)},
                    ],
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": _strict(schema)}},
        )
        if self.spec.effort:
            kwargs["output_config"]["effort"] = self.spec.effort
        kwargs.update(self.spec.extra)
        return kwargs

    def _parse(self, ts: TaskSet, qids: list[str], resp) -> RawResult:
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        Decision = build_decision_model(ts, qids)
        obj = Decision.model_validate_json(text)
        probs, labels = parse_decisions(obj, qids)
        u = resp.usage
        return RawResult(
            p_positive=probs,
            labels=labels,
            confidence={q: None for q in qids},
            resolved_model=resp.model,
            input_tokens=int(u.input_tokens or 0) + int(getattr(u, "cache_read_input_tokens", 0) or 0) + int(getattr(u, "cache_creation_input_tokens", 0) or 0),
            output_tokens=int(u.output_tokens or 0),
            cached_tokens=int(getattr(u, "cache_read_input_tokens", 0) or 0),
            cache_write_tokens=int(getattr(u, "cache_creation_input_tokens", 0) or 0),
            pricing_mode="batch" if self.batch else "standard",
            raw={"stop_reason": resp.stop_reason},
        )

    def cost(self, r: RawResult) -> tuple[float, float]:
        s = self.spec
        listed = s.cost_usd(r.input_tokens, r.output_tokens)
        uncached = r.input_tokens - r.cached_tokens - r.cache_write_tokens
        paid = (
            uncached * s.input_per_mtok
            + r.cached_tokens * s.input_per_mtok * CACHE_READ_MULT
            + r.cache_write_tokens * s.input_per_mtok * CACHE_WRITE_MULT
            + r.output_tokens * s.output_per_mtok
        ) / 1e6
        if r.pricing_mode == "batch":
            paid *= BATCH_MULT
        return paid, listed

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        resp = await self.client.messages.create(**self._kwargs(ts, qids, doc))
        return self._parse(ts, qids, resp)

    # ---- Message Batches API -------------------------------------------------
    async def run_batch(self, ts: TaskSet, units: list[tuple[list[str], Document]], poll_s: float = 20.0, log=print):
        """Submit units as one or more message batches; yield (unit_index, RawResult|Exception)."""
        results: dict[int, RawResult | Exception] = {}
        CHUNK = 10_000
        for start in range(0, len(units), CHUNK):
            chunk = units[start : start + CHUNK]
            reqs = [
                {"custom_id": f"u{start + i}", "params": self._kwargs(ts, qids, doc)}
                for i, (qids, doc) in enumerate(chunk)
            ]
            batch = await self.client.messages.batches.create(requests=reqs)
            log(f"[anthropic batch] {batch.id} submitted with {len(reqs)} requests")
            t0 = time.time()
            while True:
                await asyncio.sleep(poll_s)
                b = await self.client.messages.batches.retrieve(batch.id)
                c = b.request_counts
                if b.processing_status == "ended":
                    log(f"[anthropic batch] {batch.id} ended in {time.time()-t0:.0f}s: ok={c.succeeded} err={c.errored} exp={c.expired}")
                    break
                if int(time.time() - t0) % 300 < poll_s:
                    log(f"[anthropic batch] {batch.id} {b.processing_status}: {c.processing} processing, {c.succeeded} done")
            async for item in await self.client.messages.batches.results(batch.id):
                idx = int(item.custom_id[1:])
                qids, doc = units[idx]
                if item.result.type == "succeeded":
                    try:
                        results[idx] = self._parse(ts, qids, item.result.message)
                    except Exception as e:  # noqa: BLE001
                        results[idx] = e
                else:
                    results[idx] = RuntimeError(f"batch item {item.result.type}: {getattr(item.result, 'error', '')}")
        return results

    async def aclose(self) -> None:
        await self.client.close()


def _strict(schema: dict) -> dict:
    """Anthropic structured outputs want additionalProperties: false on objects."""
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node.setdefault("additionalProperties", False)
            if node.get("type") == "number":
                node.pop("minimum", None)
                node.pop("maximum", None)
            for v in list(node.values()):
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(schema)
    return schema

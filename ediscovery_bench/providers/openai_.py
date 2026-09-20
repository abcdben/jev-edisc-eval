from __future__ import annotations

import openai

from ..tasks import Document, TaskSet
from .base import Provider, RawResult
from .llm_common import SYSTEM_PROMPT, build_decision_model, build_doc_suffix, build_prefix, parse_decisions

CACHE_READ_MULT = 0.10
FLEX_MULT = 0.50


def _cache_key(name: str, qids: list[str], phrasing: str) -> str:
    import hashlib

    h = hashlib.sha1(("+".join(qids) + ":" + phrasing).encode()).hexdigest()[:16]
    return f"{name[:40]}-{h}"


class OpenAIProvider(Provider):
    def __init__(self, spec, phrasing: str = "rfp", flex: bool = True):
        super().__init__(spec)
        self.client = openai.AsyncOpenAI(max_retries=6, timeout=300.0)
        self.phrasing = phrasing
        self.flex = flex

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        Decision = build_decision_model(ts, qids)
        kwargs: dict = {}
        if self.spec.effort:
            kwargs["reasoning"] = {"effort": self.spec.effort}
        if self.flex:
            kwargs["service_tier"] = "flex"
        kwargs.update(self.spec.extra)
        # prefix first so the automatic prompt cache can hit on the shared part
        prompt = build_prefix(ts, qids, self.phrasing) + "\n\n" + build_doc_suffix(doc)
        try:
            resp = await self.client.responses.parse(
                model=self.spec.model_id,
                instructions=SYSTEM_PROMPT,
                input=prompt,
                text_format=Decision,
                store=False,
                prompt_cache_key=_cache_key(ts.name, qids, self.phrasing),
                **kwargs,
            )
        except openai.BadRequestError as e:
            if self.flex and "service_tier" in str(e):
                self.flex = False  # model doesn't support flex; fall back silently
                kwargs.pop("service_tier", None)
                resp = await self.client.responses.parse(
                    model=self.spec.model_id, instructions=SYSTEM_PROMPT, input=prompt,
                    text_format=Decision, store=False, **kwargs,
                )
            else:
                raise
        obj = resp.output_parsed
        if obj is None:
            raise RuntimeError("no parsed output")
        probs, labels = parse_decisions(obj, qids)
        u = resp.usage
        cached = int(u.input_tokens_details.cached_tokens or 0) if (u and u.input_tokens_details) else 0
        reasoning = int(u.output_tokens_details.reasoning_tokens or 0) if (u and u.output_tokens_details) else 0
        tier = getattr(resp, "service_tier", None) or ("flex" if self.flex else "default")
        return RawResult(
            p_positive=probs,
            labels=labels,
            confidence={q: None for q in qids},
            resolved_model=resp.model,
            input_tokens=int(u.input_tokens or 0) if u else 0,
            output_tokens=int(u.output_tokens or 0) if u else 0,
            cached_tokens=cached,
            pricing_mode="flex" if tier == "flex" else "standard",
            raw={"reasoning_tokens": reasoning, "service_tier": tier},
        )

    def cost(self, r: RawResult) -> tuple[float, float]:
        s = self.spec
        listed = s.cost_usd(r.input_tokens, r.output_tokens)
        paid = (
            (r.input_tokens - r.cached_tokens) * s.input_per_mtok
            + r.cached_tokens * s.input_per_mtok * CACHE_READ_MULT
            + r.output_tokens * s.output_per_mtok
        ) / 1e6
        if r.pricing_mode == "flex":
            paid *= FLEX_MULT
        return paid, listed

    async def aclose(self) -> None:
        await self.client.close()

from __future__ import annotations

import os

from google import genai
from google.genai import types as gt

from ..tasks import Document, TaskSet
from .base import Provider, RawResult
from .llm_common import SYSTEM_PROMPT, build_decision_model, build_doc_suffix, build_prefix, parse_decisions

CACHE_READ_MULT = 0.10


class GeminiProvider(Provider):
    def __init__(self, spec, phrasing: str = "rfp"):
        super().__init__(spec)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(
            api_key=api_key,
            http_options=gt.HttpOptions(timeout=180_000, retry_options=gt.HttpRetryOptions(attempts=6, max_delay=30.0)),
        )
        self.phrasing = phrasing

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        Decision = build_decision_model(ts, qids)
        config = gt.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=Decision,
            thinking_config=gt.ThinkingConfig(thinking_level=self.spec.effort) if self.spec.effort else None,
            **self.spec.extra,
        )
        # prefix first: Gemini 3.x implicit caching keys on the shared prompt prefix
        prompt = build_prefix(ts, qids, self.phrasing) + "\n\n" + build_doc_suffix(doc)
        resp = await self.client.aio.models.generate_content(model=self.spec.model_id, contents=prompt, config=config)
        obj = resp.parsed
        if obj is None:
            text = "".join(
                p.text
                for c in (resp.candidates or [])
                for p in (c.content.parts or [])
                if getattr(p, "text", None) and not getattr(p, "thought", False)
            )
            obj = Decision.model_validate_json(text)
        probs, labels = parse_decisions(obj, qids)
        um = resp.usage_metadata
        in_tok = int(um.prompt_token_count or 0) if um else 0
        thoughts = int(um.thoughts_token_count or 0) if um else 0
        out_tok = (int(um.candidates_token_count or 0) + thoughts) if um else 0
        cached = int(um.cached_content_token_count or 0) if um else 0
        return RawResult(
            p_positive=probs,
            labels=labels,
            confidence={q: None for q in qids},
            resolved_model=getattr(resp, "model_version", None) or self.spec.model_id,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cached_tokens=cached,
            raw={"thoughts_tokens": thoughts},
        )

    def cost(self, r: RawResult) -> tuple[float, float]:
        s = self.spec
        listed = s.cost_usd(r.input_tokens, r.output_tokens)
        paid = (
            (r.input_tokens - r.cached_tokens) * s.input_per_mtok
            + r.cached_tokens * s.input_per_mtok * CACHE_READ_MULT
            + r.output_tokens * s.output_per_mtok
        ) / 1e6
        return paid, listed

    async def aclose(self) -> None:
        try:
            await self.client.aio.aclose()
        except Exception:  # noqa: BLE001
            pass

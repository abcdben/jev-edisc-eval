"""Minimal async free-text completion client for the probe, one per vendor.

Uses the same SDKs, model ids and floor effort settings as the classification providers
(config.MODELS), but returns plain text rather than a structured decision. Temperature 0 where
the vendor accepts it; falls back to the default silently when the model rejects it.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

from ..config import ModelSpec


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    resolved_model: str
    latency_s: float
    cost_usd: float
    temperature_applied: bool


class TextClient:
    def __init__(self, spec: ModelSpec):
        self.spec = spec
        self._temp_ok = True  # flips to False if the vendor rejects temperature=0
        p = spec.provider
        if p == "openai":
            import openai

            self.client = openai.AsyncOpenAI(max_retries=6, timeout=180.0)
        elif p == "anthropic":
            import anthropic

            self.client = anthropic.AsyncAnthropic(max_retries=5, timeout=180.0)
        elif p == "gemini":
            from google import genai
            from google.genai import types as gt

            self.client = genai.Client(
                api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
                http_options=gt.HttpOptions(timeout=180_000, retry_options=gt.HttpRetryOptions(attempts=6, max_delay=30.0)),
            )
        else:
            raise ValueError(f"contamination probe supports openai/anthropic/gemini, not {p}")

    async def complete(self, system: str, user: str, max_tokens: int = 400) -> Completion:
        t0 = time.perf_counter()
        p = self.spec.provider
        if p == "openai":
            text, i, o, m = await self._openai(system, user, max_tokens)
        elif p == "anthropic":
            text, i, o, m = await self._anthropic(system, user, max_tokens)
        else:
            text, i, o, m = await self._gemini(system, user, max_tokens)
        return Completion(text, i, o, m, time.perf_counter() - t0, self.spec.cost_usd(i, o), self._temp_ok)

    # ---- vendors -------------------------------------------------------------------------------
    async def _openai(self, system, user, max_tokens):
        import openai

        kwargs: dict = dict(model=self.spec.model_id, instructions=system, input=user, store=False, max_output_tokens=max_tokens)
        if self.spec.effort:
            kwargs["reasoning"] = {"effort": self.spec.effort}
        for attempt in range(2):
            try:
                if self._temp_ok:
                    kwargs["temperature"] = 0
                else:
                    kwargs.pop("temperature", None)
                resp = await self.client.responses.create(**kwargs)
                break
            except openai.BadRequestError as e:
                if self._temp_ok and "temperature" in str(e).lower():
                    self._temp_ok = False
                    continue
                raise
        u = resp.usage
        return (resp.output_text or "").strip(), int(u.input_tokens or 0), int(u.output_tokens or 0), resp.model

    async def _anthropic(self, system, user, max_tokens):
        import anthropic

        thinking = self.spec.extra.get("thinking")
        kwargs: dict = dict(
            model=self.spec.model_id,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if thinking:
            kwargs["thinking"] = thinking
        if self.spec.effort:
            kwargs["output_config"] = {"effort": self.spec.effort}
        for attempt in range(2):
            try:
                if self._temp_ok:
                    kwargs["extra_body"] = {"temperature": 0}
                else:
                    kwargs.pop("extra_body", None)
                resp = await self.client.messages.create(**kwargs)
                break
            except anthropic.BadRequestError as e:
                if self._temp_ok and "temperature" in str(e).lower():
                    self._temp_ok = False
                    continue
                raise
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        u = resp.usage
        return text, int(u.input_tokens or 0), int(u.output_tokens or 0), resp.model

    async def _gemini(self, system, user, max_tokens):
        from google.genai import types as gt

        config = gt.GenerateContentConfig(
            system_instruction=system,
            temperature=0 if self._temp_ok else None,
            max_output_tokens=max_tokens + 2048,  # thinking tokens count against the cap on 3.x
            thinking_config=gt.ThinkingConfig(thinking_level=self.spec.effort) if self.spec.effort else None,
        )
        resp = await self.client.aio.models.generate_content(model=self.spec.model_id, contents=user, config=config)
        text = "".join(
            p.text
            for c in (resp.candidates or [])
            for p in ((c.content.parts if c.content else None) or [])
            if getattr(p, "text", None) and not getattr(p, "thought", False)
        ).strip()
        um = resp.usage_metadata
        in_tok = int(um.prompt_token_count or 0) if um else 0
        out_tok = (int(um.candidates_token_count or 0) + int(um.thoughts_token_count or 0)) if um else 0
        return text, in_tok, out_tok, getattr(resp, "model_version", None) or self.spec.model_id

    async def aclose(self) -> None:
        try:
            if self.spec.provider == "gemini":
                await self.client.aio.aclose()
            else:
                await self.client.close()
        except Exception:  # noqa: BLE001
            pass

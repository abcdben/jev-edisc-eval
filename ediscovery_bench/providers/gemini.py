from __future__ import annotations

import os

from google import genai
from google.genai import types as gt

from ..tasks import Document, Task
from .base import Provider
from .llm_common import SYSTEM_PROMPT, build_decision_model, build_user_prompt, decision_to_probs


class GeminiProvider(Provider):
    def __init__(self, spec):
        super().__init__(spec)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(
            api_key=api_key,
            http_options=gt.HttpOptions(timeout=120_000, retry_options=gt.HttpRetryOptions(attempts=5)),
        )
        self._models: dict[str, type] = {}

    def _decision_model(self, task: Task):
        if task.name not in self._models:
            self._models[task.name] = build_decision_model(task)
        return self._models[task.name]

    async def _classify(self, task: Task, doc: Document):
        Decision = self._decision_model(task)
        config = gt.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=Decision,
            thinking_config=gt.ThinkingConfig(thinking_level=self.spec.effort) if self.spec.effort else None,
            **self.spec.extra,
        )
        resp = await self.client.aio.models.generate_content(
            model=self.spec.model_id,
            contents=build_user_prompt(task, doc),
            config=config,
        )
        decision = resp.parsed
        if decision is None:
            # Fall back: strip any thought parts and parse the text ourselves.
            text = "".join(
                p.text
                for c in (resp.candidates or [])
                for p in (c.content.parts or [])
                if getattr(p, "text", None) and not getattr(p, "thought", False)
            )
            decision = Decision.model_validate_json(text)
        probs, label = decision_to_probs(decision, task)
        um = resp.usage_metadata
        in_tok = int(um.prompt_token_count or 0) if um else 0
        # Gemini bills thinking tokens as output; fold them in.
        out_tok = (
            int((um.candidates_token_count or 0) + (um.thoughts_token_count or 0)) if um else 0
        )
        resolved = getattr(resp, "model_version", None) or self.spec.model_id
        return (
            probs,
            label,
            None,
            resolved,
            in_tok,
            out_tok,
            {"thoughts_tokens": int(um.thoughts_token_count or 0) if um else 0},
        )

    async def aclose(self) -> None:
        try:
            await self.client.aio.aclose()
        except Exception:  # noqa: BLE001
            pass

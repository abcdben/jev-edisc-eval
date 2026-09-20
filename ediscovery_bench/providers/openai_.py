from __future__ import annotations

import openai

from ..tasks import Document, Task
from .base import Provider
from .llm_common import SYSTEM_PROMPT, build_decision_model, build_user_prompt, decision_to_probs


class OpenAIProvider(Provider):
    def __init__(self, spec):
        super().__init__(spec)
        self.client = openai.AsyncOpenAI(max_retries=4, timeout=120.0)
        self._models: dict[str, type] = {}

    def _decision_model(self, task: Task):
        if task.name not in self._models:
            self._models[task.name] = build_decision_model(task)
        return self._models[task.name]

    async def _classify(self, task: Task, doc: Document):
        Decision = self._decision_model(task)
        kwargs: dict = {}
        if self.spec.effort:
            kwargs["reasoning"] = {"effort": self.spec.effort}
        kwargs.update(self.spec.extra)

        resp = await self.client.responses.parse(
            model=self.spec.model_id,
            instructions=SYSTEM_PROMPT,
            input=build_user_prompt(task, doc),
            text_format=Decision,
            store=False,
            **kwargs,
        )
        decision = resp.output_parsed
        if decision is None:
            raise RuntimeError("no parsed output")
        probs, label = decision_to_probs(decision, task)
        usage = resp.usage
        reasoning_tokens = 0
        if usage and usage.output_tokens_details:
            reasoning_tokens = int(usage.output_tokens_details.reasoning_tokens or 0)
        return (
            probs,
            label,
            None,
            resp.model,
            int(usage.input_tokens or 0) if usage else 0,
            int(usage.output_tokens or 0) if usage else 0,
            {"reasoning_tokens": reasoning_tokens},
        )

    async def aclose(self) -> None:
        await self.client.close()

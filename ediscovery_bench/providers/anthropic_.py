from __future__ import annotations

import anthropic

from ..tasks import Document, Task
from .base import Provider
from .llm_common import SYSTEM_PROMPT, build_decision_model, build_user_prompt, decision_to_probs


class AnthropicProvider(Provider):
    def __init__(self, spec):
        super().__init__(spec)
        self.client = anthropic.AsyncAnthropic(max_retries=4, timeout=120.0)
        self._models: dict[str, type] = {}

    def _decision_model(self, task: Task):
        if task.name not in self._models:
            self._models[task.name] = build_decision_model(task)
        return self._models[task.name]

    async def _classify(self, task: Task, doc: Document):
        Decision = self._decision_model(task)
        kwargs: dict = {}
        if self.spec.effort:
            kwargs["output_config"] = {"effort": self.spec.effort}
        kwargs.update(self.spec.extra)

        resp = await self.client.messages.parse(
            model=self.spec.model_id,
            max_tokens=4096,  # thinking tokens count toward this on Opus 5
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(task, doc)}],
            output_format=Decision,
            **kwargs,
        )
        decision = resp.parsed_output
        if decision is None:
            raise RuntimeError(f"no parsed output; stop_reason={resp.stop_reason}")
        probs, label = decision_to_probs(decision, task)
        usage = resp.usage
        return (
            probs,
            label,
            None,
            resp.model,
            int(usage.input_tokens or 0),
            int(usage.output_tokens or 0),
            {"stop_reason": resp.stop_reason},
        )

    async def aclose(self) -> None:
        await self.client.close()

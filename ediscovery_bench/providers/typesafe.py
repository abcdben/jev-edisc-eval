from __future__ import annotations

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, NoulCriteria, RetryPolicy

from ..tasks import Document, Task
from .base import Provider


class TypeSafeProvider(Provider):
    def __init__(self, spec):
        super().__init__(spec)
        self.client = AsyncTypeSafeClient(
            model=spec.model_id,
            retry=RetryPolicy(max_retries=4, backoff_max=10.0, timeout=60.0),
            timeout=60.0,
        )

    def _state(self, task: Task, doc: Document):
        # Jev takes structured state. Keep matter context and the document as
        # separate named fields so instructions can refer to them literally.
        state: dict = {"document": doc.text}
        if task.context:
            state["matter_context"] = task.context
        return state

    def _questions(self, task: Task) -> dict:
        if task.jev_question == "noul":
            pos, neg = task.positive_label, task.negative_label
            return {
                "decision": Noul(
                    instructions=task.instructions,
                    criteria=NoulCriteria(true=task.labels[pos], false=task.labels[neg]),
                )
            }
        return {
            "decision": Choice(
                instructions=task.instructions,
                criteria={name: (desc or None) for name, desc in task.labels.items()},
            )
        }

    async def _classify(self, task: Task, doc: Document):
        resp = await self.client.system_one(
            state=self._state(task, doc), questions=self._questions(task)
        )
        usage = resp.usage
        in_tok = int(usage.input_tokens or 0) if usage else 0
        out_tok = int(usage.output_tokens or 0) if usage else 0

        if task.jev_question == "noul":
            ans = resp.nouls["decision"]
            p = float(ans.noul)
            probs = {task.positive_label: p, task.negative_label: 1.0 - p}
            # Noul has no separate confidence; use distance from 0.5 as the analog.
            conf = abs(p - 0.5) * 2
            return probs, None, conf, resp.model, in_tok, out_tok, {"noul": p}

        ans = resp.choices["decision"]
        probs = {k: float(v) for k, v in ans.probabilities.items()}
        return (
            probs,
            str(ans.choice),
            float(ans.confidence),
            resp.model,
            in_tok,
            out_tok,
            {"choice": ans.choice, "confidence": ans.confidence},
        )

    async def aclose(self) -> None:
        await self.client.aclose()

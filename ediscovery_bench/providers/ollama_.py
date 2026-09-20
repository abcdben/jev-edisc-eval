"""Local generative model via Ollama (/api/chat with a JSON schema `format`).

Same prompt and schema as the cloud LLM adapters so it is a like-for-like
floor: a small open model, no reasoning, temperature 0, running on this
machine. Cost is recorded as $0; wall-clock latency is real.
"""

from __future__ import annotations

import json
import os

import httpx

from ..tasks import Document, TaskSet
from .base import Provider, RawResult
from .llm_common import SYSTEM_PROMPT, build_decision_model, build_doc_suffix, build_prefix, parse_decisions


class OllamaProvider(Provider):
    def __init__(self, spec, phrasing: str = "rfp"):
        super().__init__(spec)
        self.base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0))
        self.phrasing = phrasing

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        Decision = build_decision_model(ts, qids)
        schema = Decision.model_json_schema()
        prompt = build_prefix(ts, qids, self.phrasing) + "\n\n" + build_doc_suffix(doc)
        body = {
            "model": self.spec.model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": int(self.spec.extra.get("num_ctx", 8192))},
            "keep_alive": "30m",
        }
        if self.spec.extra.get("think") is not None:
            body["think"] = bool(self.spec.extra["think"])
        last = None
        for attempt in range(3):
            r = await self.client.post(f"{self.base}/api/chat", json=body)
            if r.status_code >= 500:
                last = RuntimeError(f"ollama {r.status_code}: {r.text[:200]}")
                continue
            r.raise_for_status()
            data = r.json()
            content = (data.get("message") or {}).get("content") or ""
            try:
                obj = Decision.model_validate_json(content)
                break
            except Exception as e:  # noqa: BLE001
                last = e
                if attempt == 2:
                    raise
        else:
            raise last or RuntimeError("ollama failed")
        probs, labels = parse_decisions(obj, qids)
        return RawResult(
            p_positive=probs,
            labels=labels,
            confidence={q: None for q in qids},
            resolved_model=data.get("model") or self.spec.model_id,
            input_tokens=int(data.get("prompt_eval_count") or 0),
            output_tokens=int(data.get("eval_count") or 0),
            raw={
                "total_duration_ms": (data.get("total_duration") or 0) / 1e6,
                "eval_duration_ms": (data.get("eval_duration") or 0) / 1e6,
            },
        )

    async def aclose(self) -> None:
        await self.client.aclose()

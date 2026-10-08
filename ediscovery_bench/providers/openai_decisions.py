"""OpenAI Decisions API provider (GPT-6 Luna, `POST /v1/decisions`).

Public beta as of 2026-10-06 (docs: developers.openai.com/api/docs/guides/decisions).
Request: {model, input: str | messages, questions: [{type, name, instructions, ...}]}.
Response: {answers: [{type, name, ...}], usage}. Answer shapes:
  predicate -> {probability}
  choice    -> {choice, probabilities: [{value, probability}], confidence}
  refusal   -> {} (no decision; we surface it as p=0.5 with an error marker)

Variants (``openai-decisions@<variant>``), mirroring Jev's Noul/Choice forms:
  predicate -> one `predicate` question per RFP (Jev Noul analogue); instructions
               carry the criteria inline since predicates have no option descriptions.
  choice    -> one `choice` question per RFP (Jev Choice analogue) with the
               positive/negative labels as options and the criteria as descriptions.
  decompose -> Facets (Jev decompose analogue): one `predicate` question per facet
               the task file defines for the RFP (named ``<qid>__f<i>``), each with the
               criteria appended as in the predicate form; p(responsive) = max over the
               facets (logical OR). An RFP without facets falls back to the plain
               predicate question, exactly as Jev's lever does.
A bare ``openai-decisions`` on the CLI is expanded to all three variants; result stems
are always ``openai-decisions__<variant>[__tag]`` so they parse like ``jev__base__latency``.

`input` must be a string (or messages), so matter context + document are
flattened the same way as Jev's `state_string` variant.
"""

from __future__ import annotations

from typing import Any, Literal

import openai

from ..tasks import Document, TaskSet
from .base import Provider, RawResult

PATH = "/decisions"  # openai client base_url already ends in /v1

Form = Literal["choice", "predicate", "decompose"]
FORMS: tuple[Form, ...] = ("choice", "predicate", "decompose")


class OpenAIDecisionsProvider(Provider):
    def __init__(self, spec, variant: str | None = None):
        super().__init__(spec)
        form = variant or "choice"
        if form not in FORMS:
            raise ValueError(f"openai-decisions variant must be one of {FORMS}, got {form!r}")
        self.form: Form = form  # type: ignore[assignment]
        self.client = openai.AsyncOpenAI(max_retries=6, timeout=120.0)

    @property
    def key(self) -> str:
        return f"{self.spec.key}@{self.form}"  # always explicit, so result stems parse like jev__base

    # ---- request ---------------------------------------------------------
    @staticmethod
    def _input(ts: TaskSet, doc: Document) -> str:
        if ts.context:
            return f"MATTER BACKGROUND:\n{ts.context}\n\nDOCUMENT:\n{doc.text}"
        return doc.text

    @staticmethod
    def _predicate(ts: TaskSet, qid: str, name: str, instructions: str) -> dict[str, Any]:
        q = ts.questions[qid]
        return {
            "type": "predicate",
            "name": name,
            "instructions": (
                f"{instructions}\n\n"
                f"True ({ts.positive_label}): {q.positive_desc}\n"
                f"False ({ts.negative_label}): {q.negative_desc}"
            ),
        }

    def _plan(self, ts: TaskSet, qids: list[str]) -> dict[str, list[str]]:
        """plan[qid] = question names whose answers aggregate into qid (one name unless decomposed)."""
        plan: dict[str, list[str]] = {}
        for qid in qids:
            q = ts.questions[qid]
            if self.form == "decompose" and q.subparts:
                plan[qid] = [f"{qid}__f{i}" for i in range(len(q.subparts))]
            else:
                plan[qid] = [qid]
        return plan

    def _questions(self, ts: TaskSet, qids: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for qid in qids:
            q = ts.questions[qid]
            if self.form == "decompose" and q.subparts:
                # Jev's decompose lever: each facet is the instruction, criteria unchanged
                out += [self._predicate(ts, qid, f"{qid}__f{i}", sp) for i, sp in enumerate(q.subparts)]
            else:
                out.append(self._question(ts, qid))
        return out

    def _question(self, ts: TaskSet, qid: str) -> dict[str, Any]:
        q = ts.questions[qid]
        instructions = f"Is this document responsive to the following request for production?\n\n{q.rfp_text}"
        if self.form in ("predicate", "decompose"):  # decompose without facets falls back to the predicate
            return self._predicate(ts, qid, qid, instructions)
        return {
            "type": "choice",
            "name": qid,
            "instructions": instructions,
            "choices": [
                {"value": ts.positive_label, "description": q.positive_desc},
                {"value": ts.negative_label, "description": q.negative_desc},
            ],
        }

    def _body(self, ts: TaskSet, qids: list[str], doc: Document) -> dict[str, Any]:
        return {
            "model": self.spec.model_id,
            "input": self._input(ts, doc),
            "questions": self._questions(ts, qids),
            **self.spec.extra,
        }

    # ---- response --------------------------------------------------------
    @staticmethod
    def _parse(
        resp: dict[str, Any], ts: TaskSet, qids: list[str], plan: dict[str, list[str]] | None = None
    ) -> tuple[dict, dict, dict, list[str], dict[str, list[float | None]]]:
        """-> (p_positive, labels, confidence, refused, parts) keyed by qid.

        `parts[qid]` holds the per-facet probabilities when a question was decomposed
        (p = max over facets, logical OR). A refused or missing facet is recorded as
        None and left out of the max; the qid is p=0.5 / `refused` only when every
        facet is refused.
        """
        by_name = {a.get("name"): a for a in resp.get("answers") or []}
        probs: dict[str, float] = {}
        labels: dict[str, str | None] = {}
        conf: dict[str, float | None] = {}
        refused: list[str] = []
        parts: dict[str, list[float | None]] = {}
        for qid in qids:
            names = (plan or {}).get(qid) or [qid]
            if names != [qid]:
                vals: list[float | None] = []
                for n in names:
                    a = by_name.get(n)
                    bad = a is None or a.get("type") == "refusal" or a.get("probability") is None
                    vals.append(None if bad else float(a["probability"]))  # type: ignore[index]
                got = [v for v in vals if v is not None]
                parts[qid] = vals  # type: ignore[assignment]
                if not got:
                    refused.append(qid)
                    probs[qid], labels[qid], conf[qid] = 0.5, None, None
                    continue
                p = max(got)
                probs[qid] = p
                labels[qid] = ts.positive_label if p >= 0.5 else ts.negative_label
                conf[qid] = None
                continue
            a = by_name.get(qid)
            if a is None or a.get("type") == "refusal":
                refused.append(qid)
                probs[qid], labels[qid], conf[qid] = 0.5, None, None
                continue
            if a.get("type") == "predicate":
                p = float(a["probability"])
                probs[qid] = p
                labels[qid] = ts.positive_label if p >= 0.5 else ts.negative_label
                conf[qid] = None
                continue
            dist = {str(o.get("value")): float(o.get("probability", 0.0)) for o in a.get("probabilities") or []}
            choice = a.get("choice")
            p = dist.get(ts.positive_label)
            if p is None:  # distribution missing; fall back to choice + confidence
                c = a.get("confidence")
                if choice is not None and c is not None:
                    p = float(c) if str(choice) == ts.positive_label else 1.0 - float(c)
            probs[qid] = float(p) if p is not None else 0.5
            labels[qid] = str(choice) if choice is not None else None
            conf[qid] = float(a["confidence"]) if a.get("confidence") is not None else None
        return probs, labels, conf, refused, parts

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        resp = await self.client.post(PATH, body=self._body(ts, qids, doc), cast_to=dict)
        probs, labels, conf, refused, parts = self._parse(resp, ts, qids, self._plan(ts, qids))
        u = resp.get("usage") or {}
        ud = u.get("input_tokens_details") or {}
        raw: dict[str, Any] = {"form": self.form}
        for qid, vals in parts.items():
            raw[f"{qid}_parts"] = vals  # same key as Jev's decompose rows
        if refused:
            raw["refused"] = refused
        return RawResult(
            p_positive=probs,
            labels=labels,
            confidence=conf,
            resolved_model=str(resp.get("model") or self.spec.model_id),
            input_tokens=int(u.get("input_tokens") or 0),
            output_tokens=int(u.get("output_tokens") or 0),  # always 0; billed on input only
            cached_tokens=int(ud.get("cached_tokens") or 0),
            cache_write_tokens=int(ud.get("cache_write_tokens") or 0),
            raw=raw,
        )

    async def aclose(self) -> None:
        await self.client.close()

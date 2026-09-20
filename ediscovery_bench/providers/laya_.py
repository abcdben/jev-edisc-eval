"""Laya (ConvAI) local System 1 provider.

Same question surface as Jev (Noul / Choice / Score) so the ablation variants
are byte-comparable. Weights run on this machine (MPS on Apple Silicon, else CPU).
No API key, $0. Context is 512 tokens on the English checkpoint — long RFPs and
documents are truncated by the SDK; we log the token count we actually sent.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from ..config import ModelSpec
from ..tasks import Document, TaskSet
from .base import Provider, RawResult
from .typesafe import SCORE_LEVELS, JevConfig, VARIANTS, variant_key

# One process-wide agent per (repo, subfolder) so sequential jobs don't reload 400M params.
_AGENTS: dict[tuple[str, str | None], Any] = {}
_AGENT_LOCK = asyncio.Lock()


def _get_agent(model_id: str, subfolder: str | None):
    key = (model_id, subfolder)
    if key not in _AGENTS:
        os.environ.setdefault("USE_TF", "0")
        import laya

        _AGENTS[key] = laya.load(model_id, subfolder=subfolder)
    return _AGENTS[key]


class LayaProvider(Provider):
    def __init__(self, spec: ModelSpec, cfg: JevConfig | None = None, variant: str = "base"):
        super().__init__(spec)
        self.cfg = cfg or VARIANTS[variant]
        self.variant = variant
        self.subfolder = spec.extra.get("subfolder")
        self._agent = None

    @property
    def key(self) -> str:
        prefix = "laya-typed" if self.subfolder else "laya"
        return f"{prefix}@{self.variant}"

    def _state(self, ts: TaskSet, doc: Document):
        ctx = ts.context if self.cfg.context else ""
        if self.cfg.state == "string":
            return (f"MATTER BACKGROUND:\n{ctx}\n\nDOCUMENT:\n{doc.text}") if ctx else doc.text
        st: dict = {"document": doc.text}
        if ctx:
            st["matter_context"] = ctx
        return st

    def _instr(self, q, ts: TaskSet | None = None) -> str:
        if self.cfg.phrasing == "literal" and q.literal:
            return q.literal
        return f"Is this document responsive to the following request for production?\n\n{q.rfp_text}"

    def _noul(self, ts: TaskSet, q, instructions: str) -> dict:
        d: dict = {"type": "noul", "instructions": instructions}
        if self.cfg.criteria == "none":
            return d
        if self.cfg.criteria == "structured" and q.structured:
            d["criteria"] = {
                "true": q.structured.get(ts.positive_label),
                "false": q.structured.get(ts.negative_label),
            }
        else:
            d["criteria"] = {"true": q.positive_desc, "false": q.negative_desc}
        return d

    def _choice(self, ts: TaskSet, q, instructions: str) -> dict:
        if self.cfg.criteria == "none":
            crit = {ts.positive_label: None, ts.negative_label: None}
        elif self.cfg.criteria == "structured" and q.structured:
            crit = {
                ts.positive_label: q.structured.get(ts.positive_label),
                ts.negative_label: q.structured.get(ts.negative_label),
            }
        else:
            crit = {ts.positive_label: q.positive_desc, ts.negative_label: q.negative_desc}
        return {"type": "choice", "instructions": instructions, "criteria": crit}

    def _score(self, ts: TaskSet, q, instructions: str) -> dict:
        instr = instructions
        if self.cfg.criteria != "none":
            instr = f"{instructions}\n\nResponsive means: {q.positive_desc}\nNot responsive means: {q.negative_desc}"
        return {"type": "score", "instructions": instr, "criteria": SCORE_LEVELS}

    def _questions(self, ts: TaskSet, qids: list[str]) -> tuple[dict, dict[str, list[tuple[str, str]]]]:
        questions: dict = {}
        plan: dict[str, list[tuple[str, str]]] = {}
        for qid in qids:
            q = ts.questions[qid]
            keys: list[tuple[str, str]] = []
            if self.cfg.decompose and q.subparts:
                for i, sp in enumerate(q.subparts):
                    k = f"{qid}__sp{i}"
                    questions[k] = self._noul(ts, q, sp)
                    keys.append((k, "noul"))
                plan[qid] = keys
                continue
            if self.cfg.ensemble:
                phrasings = [
                    f"Is this document responsive to the following request for production?\n\n{q.rfp_text}",
                    q.literal or q.rfp_text,
                    f"This document is responsive to the request: {q.title}. {q.positive_desc}",
                ]
                for i, ph in enumerate(phrasings):
                    k = f"{qid}__e{i}"
                    questions[k] = self._noul(ts, q, ph)
                    keys.append((k, "noul"))
                plan[qid] = keys
                continue
            instr = self._instr(q)
            if self.cfg.form == "noul":
                questions[qid] = self._noul(ts, q, instr)
                keys.append((qid, "noul"))
            elif self.cfg.form == "choice":
                questions[qid] = self._choice(ts, q, instr)
                keys.append((qid, "choice"))
            else:
                questions[qid] = self._score(ts, q, instr)
                keys.append((qid, "score"))
            plan[qid] = keys
        if self.cfg.gate and ts.gate_question:
            questions["__gate__"] = {"type": "noul", "instructions": ts.gate_question}
        return questions, plan

    def _predict_sync(self, state, questions) -> dict:
        if self._agent is None:
            self._agent = _get_agent(self.spec.model_id, self.subfolder)
        return self._agent.system_one(state, questions)

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        questions, plan = self._questions(ts, qids)
        resp = await asyncio.to_thread(self._predict_sync, self._state(ts, doc), questions)
        answers = resp.get("answers") or {}
        usage = resp.get("usage") or {}
        gate = float(answers["__gate__"]["noul"]) if (self.cfg.gate and "__gate__" in answers) else None
        probs: dict[str, float] = {}
        labels: dict[str, str | None] = {}
        conf: dict[str, float | None] = {}
        raw: dict = {"device": str(getattr(self._agent, "device", ""))}
        for qid, keys in plan.items():
            vals: list[float] = []
            c: float | None = None
            lab: str | None = None
            for k, kind in keys:
                a = answers[k]
                if kind == "noul":
                    vals.append(float(a["noul"]))
                    c = float(a.get("confidence") or 0.0)
                elif kind == "choice":
                    vals.append(float((a.get("probabilities") or {}).get(ts.positive_label, 0.0)))
                    c = float(a.get("confidence") or 0.0)
                    lab = str(a.get("choice"))
                else:
                    vals.append(float(a["score"]) / (len(SCORE_LEVELS) - 1))
                    c = float(a.get("confidence") or 0.0)
                    raw[f"{qid}_score"] = float(a["score"])
            p = max(vals) if (self.cfg.decompose and len(keys) > 1) else (sum(vals) / len(vals))
            if gate is not None:
                p = p * gate
                lab = None
            probs[qid] = p
            labels[qid] = lab
            conf[qid] = c if c is not None else abs(p - 0.5) * 2
            if len(keys) > 1:
                raw[f"{qid}_parts"] = vals
        if gate is not None:
            raw["gate"] = gate
        return RawResult(
            p_positive=probs,
            labels=labels,
            confidence=conf,
            resolved_model=str(resp.get("model") or self.spec.model_id),
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            raw=raw,
        )

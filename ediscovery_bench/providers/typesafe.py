"""Jev provider with ablation levers.

Baseline ("jev@base"): Noul; verbatim RFP text as instructions; positive/negative
descriptions as true/false criteria; structured state {matter_context, document};
one request per unit of work; pinned model.

Each lever changes exactly one thing from the baseline. `RECIPE` is filled in
after the one-at-a-time results are read.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, NoulCriteria, RetryPolicy, Score

from ..config import ModelSpec
from ..tasks import Document, Question, TaskSet
from .base import Provider, RawResult

SCORE_LEVELS = [
    "Clearly not responsive to the request",
    "Probably not responsive",
    "Borderline; a reviewer could go either way",
    "Probably responsive",
    "Clearly responsive to the request",
]


@dataclass(frozen=True)
class JevConfig:
    form: Literal["noul", "choice", "score"] = "noul"
    criteria: Literal["desc", "none", "structured"] = "desc"
    phrasing: Literal["rfp", "literal"] = "rfp"
    context: bool = True
    state: Literal["structured", "string"] = "structured"
    gate: bool = False
    ensemble: bool = False  # average Noul over 3 phrasings
    decompose: bool = False  # OR over subparts where defined
    model_id: str = "jev-1.13.0"


VARIANTS: dict[str, JevConfig] = {
    "base": JevConfig(),
    "choice": JevConfig(form="choice"),
    "score": JevConfig(form="score"),
    "crit_none": JevConfig(criteria="none"),
    "crit_struct": JevConfig(criteria="structured"),
    "literal": JevConfig(phrasing="literal"),
    "no_context": JevConfig(context=False),
    "state_string": JevConfig(state="string"),
    "gate": JevConfig(gate=True),
    "ensemble": JevConfig(ensemble=True),
    "decompose": JevConfig(decompose=True),
    "preview": JevConfig(model_id="jev-preview"),
    # filled in after reading the ablation table; see design/05_jev_recipe.md
    "recipe": JevConfig(),
}


def set_recipe(cfg: JevConfig) -> None:
    VARIANTS["recipe"] = cfg


def variant_key(name: str) -> str:
    return f"jev@{name}"


class TypeSafeProvider(Provider):
    def __init__(self, spec: ModelSpec, cfg: JevConfig | None = None, variant: str = "base"):
        super().__init__(spec)
        self.cfg = cfg or VARIANTS[variant]
        self.variant = variant
        self.client = AsyncTypeSafeClient(
            model=self.cfg.model_id,
            retry=RetryPolicy(max_retries=5, backoff_max=15.0, timeout=90.0),
            timeout=90.0,
        )

    @property
    def key(self) -> str:
        return variant_key(self.variant)

    # ---- state -----------------------------------------------------------
    def _state(self, ts: TaskSet, doc: Document):
        ctx = ts.context if self.cfg.context else ""
        if self.cfg.state == "string":
            return (f"MATTER BACKGROUND:\n{ctx}\n\nDOCUMENT:\n{doc.text}") if ctx else doc.text
        st: dict = {"document": doc.text}
        if ctx:
            st["matter_context"] = ctx
        return st

    # ---- questions -------------------------------------------------------
    def _instr(self, q: Question) -> str:
        if self.cfg.phrasing == "literal" and q.literal:
            return q.literal
        return f"Is this document responsive to the following request for production?\n\n{q.rfp_text}"

    def _noul(self, ts: TaskSet, q: Question, instructions: str) -> Noul:
        if self.cfg.criteria == "none":
            return Noul(instructions=instructions)
        if self.cfg.criteria == "structured" and q.structured:
            return Noul(
                instructions=instructions,
                criteria=NoulCriteria(
                    true=q.structured.get(ts.positive_label), false=q.structured.get(ts.negative_label)
                ),
            )
        return Noul(instructions=instructions, criteria=NoulCriteria(true=q.positive_desc, false=q.negative_desc))

    def _choice(self, ts: TaskSet, q: Question, instructions: str) -> Choice:
        if self.cfg.criteria == "none":
            crit = {ts.positive_label: None, ts.negative_label: None}
        elif self.cfg.criteria == "structured" and q.structured:
            crit = {ts.positive_label: q.structured.get(ts.positive_label), ts.negative_label: q.structured.get(ts.negative_label)}
        else:
            crit = {ts.positive_label: q.positive_desc, ts.negative_label: q.negative_desc}
        return Choice(instructions=instructions, criteria=crit)

    def _score(self, ts: TaskSet, q: Question, instructions: str) -> Score:
        instr = instructions
        if self.cfg.criteria != "none":
            instr = f"{instructions}\n\nResponsive means: {q.positive_desc}\nNot responsive means: {q.negative_desc}"
        return Score(instructions=instr, criteria=SCORE_LEVELS)

    def _questions(self, ts: TaskSet, qids: list[str]) -> tuple[dict, dict[str, list[tuple[str, str]]]]:
        """Return (questions, plan) where plan[qid] = [(question_key, kind), ...] to aggregate."""
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
            questions["__gate__"] = Noul(instructions=ts.gate_question)
        return questions, plan

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        questions, plan = self._questions(ts, qids)
        resp = await self.client.system_one(state=self._state(ts, doc), questions=questions)
        usage = resp.usage
        in_tok = int(usage.input_tokens or 0) if usage else 0
        out_tok = int(usage.output_tokens or 0) if usage else 0

        gate = float(resp.nouls["__gate__"].noul) if (self.cfg.gate and "__gate__" in resp.nouls) else None
        probs: dict[str, float] = {}
        labels: dict[str, str | None] = {}
        conf: dict[str, float | None] = {}
        raw: dict = {}
        for qid, keys in plan.items():
            vals: list[float] = []
            c: float | None = None
            lab: str | None = None
            for k, kind in keys:
                if kind == "noul":
                    vals.append(float(resp.nouls[k].noul))
                elif kind == "choice":
                    a = resp.choices[k]
                    vals.append(float(a.probabilities.get(ts.positive_label, 0.0)))
                    c = float(a.confidence)
                    lab = str(a.choice)
                else:
                    a = resp.scores[k]
                    vals.append(float(a.score) / (len(SCORE_LEVELS) - 1))
                    c = float(a.confidence)
                    raw[f"{qid}_score"] = float(a.score)
            if self.cfg.decompose and len(keys) > 1:
                p = max(vals)  # OR over subparts
            else:
                p = sum(vals) / len(vals)
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
            resolved_model=resp.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            raw=raw,
        )

    async def aclose(self) -> None:
        await self.client.aclose()

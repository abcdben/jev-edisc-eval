"""Laya (ConvAI) local System 1 provider.

Same question surface as Jev (Noul / Choice / Score) so the ablation variants
are byte-comparable. Weights run on this machine (MPS on Apple Silicon, else CPU).
No API key, $0.

How Laya packs a call (English checkpoint):
    [CLS] head (<= head_max_len=192 tokens: type + instructions + options) [SEP] state [SEP]
with the whole thing capped at max_len=512, each option capped at 48 tokens, and
the state truncated from the right. On our corpora that means most RFP
instructions and every criterion are silently cut, 44% (Veridian) / 88%
(Mallinckrodt) of documents are cut, and the matter context is never seen.
Two Laya-specific levers address this:

  compact  -- one-line instruction and one-sentence criteria that fit the head budget
  chunk    -- slide a window over the document (sized to the state room), run each
              window, and max-pool p per question (the usual encoder-classifier trick)

`crit_struct`, `crit_none`, `no_context`, `state_string` are truncation artifacts on
Laya and are not offered as variants here.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import replace
from typing import Any

from ..config import ModelSpec
from ..tasks import Document, TaskSet
from .base import Provider, RawResult
from .typesafe import SCORE_LEVELS, JevConfig

# One process-wide agent per (repo, subfolder) so sequential jobs don't reload 400M params.
_AGENTS: dict[tuple[str, str | None], Any] = {}

LAYA_VARIANTS: dict[str, JevConfig] = {
    "base": JevConfig(),
    "choice": JevConfig(form="choice"),
    "score": JevConfig(form="score"),
    "literal": JevConfig(phrasing="literal"),
    "gate": JevConfig(gate=True),
    "ensemble": JevConfig(ensemble=True),
    "decompose": JevConfig(decompose=True),
    "compact": JevConfig(compact=True),
    "chunk": JevConfig(chunk=True),
    "recipe": JevConfig(compact=True, chunk=True),
    "recipe_choice": JevConfig(compact=True, chunk=True, form="choice"),
}

MAX_WINDOWS = 16
WINDOW_OVERLAP = 48
COMPACT_MAX_WORDS = 34  # ~45 tokens; Laya caps each option at 48


def _get_agent(model_id: str, subfolder: str | None):
    key = (model_id, subfolder)
    if key not in _AGENTS:
        os.environ.setdefault("USE_TF", "0")
        import laya

        _AGENTS[key] = laya.load(model_id, subfolder=subfolder)
    return _AGENTS[key]


def first_sentence(text: str, max_words: int = COMPACT_MAX_WORDS) -> str:
    """First sentence of `text`, cut to `max_words` words at a clause boundary if possible."""
    t = " ".join(text.split())
    m = re.match(r"(.+?[.;:])(\s|$)", t)
    s = m.group(1) if m else t
    words = s.split()
    if len(words) > max_words:
        s = " ".join(words[:max_words]).rstrip(",;:")
    return s.rstrip(".;:")


class LayaProvider(Provider):
    def __init__(self, spec: ModelSpec, cfg: JevConfig | None = None, variant: str = "base"):
        super().__init__(spec)
        if cfg is None:
            if variant not in LAYA_VARIANTS:
                raise KeyError(f"unknown Laya variant {variant!r}; choose from {sorted(LAYA_VARIANTS)}")
            cfg = LAYA_VARIANTS[variant]
        self.cfg = cfg
        self.variant = variant
        self.subfolder = spec.extra.get("subfolder")
        self._agent = None

    @property
    def key(self) -> str:
        return f"{self.spec.key}@{self.variant}"

    # ---- state -------------------------------------------------------------
    def _state(self, ts: TaskSet, text: str):
        ctx = ts.context if self.cfg.context else ""
        if self.cfg.state == "string":
            return (f"MATTER BACKGROUND:\n{ctx}\n\nDOCUMENT:\n{text}") if ctx else text
        st: dict = {"document": text}
        if ctx:
            st["matter_context"] = ctx
        return st

    def _windows(self, text: str) -> list[str]:
        """Token windows sized to the state room of the loaded checkpoint."""
        if not self.cfg.chunk:
            return [text]
        agent = self._agent
        tok = agent.tok
        room = int(agent.cfg.get("max_len", 512)) - int(agent.cfg.get("head_max_len", 192)) - 3
        # JSON state wrapper costs a few tokens; leave slack so the window itself isn't cut.
        win = max(64, room - 12)
        ids = tok(text, add_special_tokens=False)["input_ids"]
        if len(ids) <= win:
            return [text]
        out: list[str] = []
        step = win - WINDOW_OVERLAP
        for start in range(0, len(ids), step):
            piece = ids[start : start + win]
            out.append(tok.decode(piece, skip_special_tokens=True))
            if start + win >= len(ids) or len(out) >= MAX_WINDOWS:
                break
        return out

    # ---- questions ---------------------------------------------------------
    def _instr(self, q) -> str:
        if self.cfg.compact:
            return f"Is this document responsive to the request for production about: {q.title}?"
        if self.cfg.phrasing == "literal" and q.literal:
            return q.literal
        return f"Is this document responsive to the following request for production?\n\n{q.rfp_text}"

    def _crit_pair(self, ts: TaskSet, q) -> tuple[str | None, str | None]:
        if self.cfg.criteria == "none":
            return None, None
        if self.cfg.compact:
            return first_sentence(q.positive_desc), first_sentence(q.negative_desc)
        if self.cfg.criteria == "structured" and q.structured:
            return q.structured.get(ts.positive_label), q.structured.get(ts.negative_label)
        return q.positive_desc, q.negative_desc

    def _noul(self, ts: TaskSet, q, instructions: str) -> dict:
        d: dict = {"type": "noul", "instructions": instructions}
        pos, neg = self._crit_pair(ts, q)
        if pos is not None:
            d["criteria"] = {"true": pos, "false": neg}
        return d

    def _choice(self, ts: TaskSet, q, instructions: str) -> dict:
        pos, neg = self._crit_pair(ts, q)
        return {
            "type": "choice",
            "instructions": instructions,
            "criteria": {ts.positive_label: pos, ts.negative_label: neg},
        }

    def _score(self, ts: TaskSet, q, instructions: str) -> dict:
        instr = instructions
        pos, neg = self._crit_pair(ts, q)
        if pos is not None:
            instr = f"{instructions}\n\nResponsive means: {pos}\nNot responsive means: {neg}"
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
            gq = first_sentence(ts.gate_question, 60) if self.cfg.compact else ts.gate_question
            questions["__gate__"] = {"type": "noul", "instructions": gq}
        return questions, plan

    # ---- inference ---------------------------------------------------------
    def _predict_sync(self, ts: TaskSet, text: str, questions: dict) -> list[dict]:
        if self._agent is None:
            self._agent = _get_agent(self.spec.model_id, self.subfolder)
        return [self._agent.system_one(self._state(ts, w), questions) for w in self._windows(text)]

    @staticmethod
    def _p_of(a: dict, kind: str, ts: TaskSet) -> float:
        if kind == "noul":
            return float(a["noul"])
        if kind == "choice":
            return float((a.get("probabilities") or {}).get(ts.positive_label, 0.0))
        return float(a["score"]) / (len(SCORE_LEVELS) - 1)

    async def _call(self, ts: TaskSet, qids: list[str], doc: Document) -> RawResult:
        questions, plan = self._questions(ts, qids)
        resps = await asyncio.to_thread(self._predict_sync, ts, doc.text, questions)
        n_win = len(resps)
        # Max-pool each answer key across windows (a doc is responsive if any part is).
        pooled: dict[str, float] = {}
        act: dict[str, float] = {}
        for resp in resps:
            for k, a in (resp.get("answers") or {}).items():
                kind = "noul" if a.get("type") == "noul" else ("choice" if a.get("type") == "choice" else "score")
                p = self._p_of(a, kind, ts)
                if k not in pooled or p > pooled[k]:
                    pooled[k] = p
                    act[k] = float((a.get("action") or {}).get("act_probability", 0.0))
        gate = pooled.get("__gate__") if self.cfg.gate else None
        probs: dict[str, float] = {}
        labels: dict[str, str | None] = {}
        conf: dict[str, float | None] = {}
        raw: dict = {"device": str(getattr(self._agent, "device", "")), "windows": n_win}
        for qid, keys in plan.items():
            vals = [pooled[k] for k, _ in keys]
            p = max(vals) if (self.cfg.decompose and len(keys) > 1) else (sum(vals) / len(vals))
            lab: str | None = None
            if len(keys) == 1 and keys[0][1] == "choice" and n_win == 1:
                lab = ts.positive_label if p >= 0.5 else ts.negative_label
            if gate is not None:
                p = p * gate
            probs[qid] = p
            labels[qid] = lab
            conf[qid] = max(p, 1.0 - p)
            raw[f"{qid}_act"] = act.get(keys[0][0])
            if len(keys) > 1:
                raw[f"{qid}_parts"] = vals
        if gate is not None:
            raw["gate"] = gate
        usage_in = sum(int((r.get("usage") or {}).get("input_tokens") or 0) for r in resps)
        return RawResult(
            p_positive=probs,
            labels=labels,
            confidence=conf,
            resolved_model=f"{resps[0].get('model') or self.spec.model_id}" + (f"[{self.subfolder}]" if self.subfolder else ""),
            input_tokens=usage_in,
            output_tokens=0,
            raw=raw,
        )


def variant_with(base: str, **kw) -> JevConfig:
    return replace(LAYA_VARIANTS[base], **kw)

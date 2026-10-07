"""Task sets, questions, and documents.

A *task set* is one matter with shared `context` and N binary questions (RFPs /
issues). Every question is answered as responsive / not_responsive.

Task-set YAML (see tasks/veridian.yaml):

    name: veridian
    positive_label: responsive
    negative_label: not_responsive
    context: |
      ...
    gate_question: "..."        # optional; used by the Jev relevance-gate lever
    questions:
      rfp01_recall:
        title: ...
        rfp_text: |            # verbatim request; what every model gets by default
        literal: |             # plain, literal rewrite (Jev lever; also LLM fairness re-run)
        positive_desc: |       # what responsive means
        negative_desc: |       # what not responsive means
        structured: {...}      # JSON-structured criteria (Jev lever)
        subparts: [...]        # decomposition into atomic yes/no questions (Jev lever)

Corpus JSONL, one document per line:

    {"id": "...", "text": "...",
     "labels": {"rfp01_recall": "responsive", ...},   # absent question => negative
     "gray": ["rfp06_marketing"],                       # questions where gold is debatable
     "meta": {...}}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml


@dataclass(frozen=True)
class Question:
    id: str
    title: str
    rfp_text: str
    positive_desc: str
    negative_desc: str
    literal: str = ""
    structured: dict | None = None
    subparts: tuple[str, ...] = ()
    breadth: str = ""
    richness: str = ""
    pair: str = ""  # for broad/narrow pairs on the same issue (Mallinckrodt)

    @property
    def instructions(self) -> str:
        return self.rfp_text


@dataclass(frozen=True)
class TaskSet:
    name: str
    context: str
    questions: dict[str, Question]
    positive_label: str = "responsive"
    negative_label: str = "not_responsive"
    gate_question: str = ""
    source: str = ""

    @property
    def qids(self) -> list[str]:
        return list(self.questions)

    def labels_for(self, q: Question) -> dict[str, str]:
        return {self.positive_label: q.positive_desc.strip(), self.negative_label: q.negative_desc.strip()}

    def subset(self, qids: list[str]) -> "TaskSet":
        return TaskSet(
            name=self.name,
            context=self.context,
            questions={q: self.questions[q] for q in qids},
            positive_label=self.positive_label,
            negative_label=self.negative_label,
            gate_question=self.gate_question,
            source=self.source,
        )

    @staticmethod
    def load(path: str | Path) -> "TaskSet":
        path = Path(path)
        raw = yaml.safe_load(path.read_text())
        qs: dict[str, Question] = {}
        for qid, q in raw["questions"].items():
            qs[qid] = Question(
                id=qid,
                title=q.get("title", qid),
                rfp_text=q["rfp_text"].strip(),
                positive_desc=q["positive_desc"].strip(),
                negative_desc=q["negative_desc"].strip(),
                literal=(q.get("literal") or "").strip(),
                structured=q.get("structured"),
                subparts=tuple(s.strip() for s in (q.get("subparts") or [])),
                breadth=q.get("breadth", ""),
                richness=q.get("richness", ""),
                pair=q.get("pair", ""),
            )
        return TaskSet(
            name=raw["name"],
            context=(raw.get("context") or "").strip(),
            questions=qs,
            positive_label=raw.get("positive_label", "responsive"),
            negative_label=raw.get("negative_label", "not_responsive"),
            gate_question=(raw.get("gate_question") or "").strip(),
            source=str(path),
        )


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    labels: dict[str, str] = field(default_factory=dict)  # qid -> gold label (absent => negative)
    gray: frozenset[str] = frozenset()  # qids where gold is debatable
    meta: dict[str, Any] = field(default_factory=dict)

    def gold(self, qid: str, negative_label: str = "not_responsive") -> str | None:
        if not self.labels and "__unlabeled__" in self.meta:
            return None
        return self.labels.get(qid, negative_label)


def load_corpus(path: str | Path, limit: int | None = None, labeled: bool = True) -> list[Document]:
    """Load a corpus JSONL. If `labeled` is False, documents carry no gold."""
    docs: list[Document] = []
    # one JSON object per "\n"-terminated line; str.splitlines would also break on U+2028 and other separators inside a document's text
    for i, line in enumerate(Path(path).read_text().split("\n")):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        labels = row.get("labels") or {}
        meta = dict(row.get("meta") or {})
        if not labeled:
            labels = {}
            meta["__unlabeled__"] = True
        docs.append(
            Document(
                id=str(row.get("id", i)),
                text=row["text"],
                labels={str(k): str(v) for k, v in labels.items()},
                gray=frozenset(row.get("gray") or []),
                meta=meta,
            )
        )
        if limit and len(docs) >= limit:
            break
    return docs


def iter_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)

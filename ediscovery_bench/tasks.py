"""Task specification: what we're asking every model to decide.

A task is a YAML file. The same instructions and label criteria are handed to
every provider, so differences in results are about the model, not the prompt.

Binary example (tasks/responsiveness.yaml):

    name: responsiveness
    kind: binary
    positive_label: responsive
    labels:
      responsive: "Document relates to ... "
      not_responsive: "Document does not relate to ..."
    context: |
      Background about the matter the reviewer would have.
    instructions: |
      The literal question to answer about the document.

Multiclass tasks set `kind: multiclass` and omit `positive_label`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Literal

import yaml

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Task:
    name: str
    kind: Literal["binary", "multiclass"]
    labels: dict[str, str]  # label -> description/criteria
    instructions: str
    context: str = ""
    positive_label: str | None = None
    # How Jev should be asked. Binary tasks default to a Noul (yes/no
    # probability), which is the most natural fit and exercises calibration.
    # Set to "choice" to force a Choice over the label set instead.
    jev_question: Literal["noul", "choice"] = "noul"
    source: str = ""

    @property
    def label_names(self) -> list[str]:
        return list(self.labels)

    @property
    def negative_label(self) -> str:
        assert self.kind == "binary" and self.positive_label
        return next(l for l in self.labels if l != self.positive_label)

    def validate(self) -> None:
        if len(self.labels) < 2:
            raise ValueError(f"task {self.name}: need at least 2 labels")
        for l in self.labels:
            if not _IDENT.match(l):
                raise ValueError(
                    f"task {self.name}: label {l!r} must be identifier-safe (letters, digits, underscore)"
                )
        if self.kind == "binary":
            if len(self.labels) != 2:
                raise ValueError(f"task {self.name}: binary task needs exactly 2 labels")
            if self.positive_label not in self.labels:
                raise ValueError(
                    f"task {self.name}: positive_label {self.positive_label!r} not in labels"
                )
        if self.jev_question == "noul" and self.kind != "binary":
            raise ValueError(f"task {self.name}: jev_question=noul only valid for binary tasks")

    @staticmethod
    def load(path: str | Path) -> "Task":
        path = Path(path)
        raw = yaml.safe_load(path.read_text())
        kind = raw.get("kind", "binary")
        task = Task(
            name=raw["name"],
            kind=kind,
            labels={str(k): (v or "") for k, v in raw["labels"].items()},
            instructions=raw["instructions"].strip(),
            context=(raw.get("context") or "").strip(),
            positive_label=raw.get("positive_label"),
            jev_question=raw.get("jev_question", "noul" if kind == "binary" else "choice"),
            source=str(path),
        )
        task.validate()
        return task


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    label: str | None = None  # gold label, if known
    meta: dict[str, Any] = field(default_factory=dict)


def load_documents(
    path: str | Path, limit: int | None = None, label_field: str = "label"
) -> list[Document]:
    """Load JSONL: one {"id", "text", "label", "meta"?} object per line.

    `label_field` selects the gold label. It is looked up first as a top-level
    key, then inside a `labels` object, so one corpus can carry several
    task labels (e.g. {"labels": {"responsiveness": ..., "privilege": ...}}).
    """
    docs: list[Document] = []
    for i, line in enumerate(Path(path).read_text().splitlines()):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        label = row.get(label_field)
        if label is None and isinstance(row.get("labels"), dict):
            label = row["labels"].get(label_field)
        docs.append(
            Document(
                id=str(row.get("id", i)),
                text=row["text"],
                label=label,
                meta=row.get("meta") or {},
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

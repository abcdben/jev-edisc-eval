"""Shared prompt + structured-output schema for the generative LLMs.

Mirrors TypeSafe's "System One LLM wrapper" approach: the LLM is constrained to
return a decision plus a probability distribution over the label set, so its
output is directly comparable to Jev's `probabilities`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, create_model

from ..tasks import Document, Task

SYSTEM_PROMPT = (
    "You are a document review classifier working on an eDiscovery matter. "
    "Read the document and the review instructions, then classify the document. "
    "Return only the structured result. Do not explain."
)


def build_user_prompt(task: Task, doc: Document) -> str:
    parts = []
    if task.context:
        parts.append(f"<matter_context>\n{task.context}\n</matter_context>")
    parts.append(f"<instructions>\n{task.instructions}\n</instructions>")
    crit = "\n".join(f"- {name}: {desc}" for name, desc in task.labels.items())
    parts.append(f"<labels>\n{crit}\n</labels>")
    parts.append(f"<document id=\"{doc.id}\">\n{doc.text}\n</document>")
    parts.append(
        "Classify the document with exactly one label. Also give your probability "
        "(0 to 1) for EACH label; the probabilities should sum to 1 and reflect how "
        "likely each label is to be the correct one."
    )
    return "\n\n".join(parts)


def build_decision_model(task: Task) -> type[BaseModel]:
    """Dynamically build:

        class Decision(BaseModel):
            label: Literal[<labels>]
            probabilities: Probabilities   # one float field per label
    """
    prob_fields = {
        name: (float, Field(ge=0.0, le=1.0, description=f"Probability that '{name}' is correct"))
        for name in task.label_names
    }
    Probabilities = create_model("Probabilities", **prob_fields)  # type: ignore[call-overload]
    label_type = Literal[tuple(task.label_names)]  # type: ignore[valid-type]
    Decision = create_model(
        "Decision",
        label=(label_type, Field(description="The single best label")),
        probabilities=(Probabilities, Field(description="Probability for each label")),
    )
    return Decision


def decision_to_probs(decision: BaseModel, task: Task) -> tuple[dict[str, float], str]:
    label = getattr(decision, "label")
    probs_obj = getattr(decision, "probabilities")
    probs = {name: float(getattr(probs_obj, name)) for name in task.label_names}
    return probs, str(label)

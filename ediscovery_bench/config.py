"""Model roster and pricing.

Prices are USD per million tokens, standard (non-batch, non-cached) tier, as
published on each vendor's pricing page on 2026-09-19. Update here if they move.

`effort` is the vendor-specific "how much should the model think" knob. We
default every LLM to its lowest universally-supported level ("low") so the
comparison against Jev (which has no reasoning phase) is about the decision
quality of a fast classifier pass, not a chain-of-thought pass. Override with
`--effort` on the CLI to test the other end of the spectrum.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Provider = Literal["typesafe", "anthropic", "openai", "gemini", "mock"]


@dataclass(frozen=True)
class ModelSpec:
    key: str  # short name used on the CLI
    provider: Provider
    model_id: str  # what gets sent on the wire
    input_per_mtok: float
    output_per_mtok: float
    size: Literal["small", "large", "n/a"] = "n/a"
    effort: str | None = None  # vendor effort/thinking level, None = vendor default
    notes: str = ""
    # Provider-specific extras (e.g. Anthropic `thinking` param)
    extra: dict = field(default_factory=dict)

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_per_mtok + output_tokens * self.output_per_mtok
        ) / 1_000_000


MODELS: dict[str, ModelSpec] = {
    # ---- TypeSafe -------------------------------------------------------
    "jev": ModelSpec(
        key="jev",
        provider="typesafe",
        model_id="jev-1.13.0",  # pinned; `jev-latest` resolves here today
        input_per_mtok=0.042,
        output_per_mtok=0.0,
        notes="System One model. Output tokens are free. Pinned so thresholds stay stable.",
    ),
    "jev-latest": ModelSpec(
        key="jev-latest",
        provider="typesafe",
        model_id="jev-latest",
        input_per_mtok=0.042,
        output_per_mtok=0.0,
        notes="Alias; moves when TypeSafe ships a new release. Response `model` field is logged.",
    ),
    # ---- Anthropic ------------------------------------------------------
    "claude-haiku-4.5": ModelSpec(
        key="claude-haiku-4.5",
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        input_per_mtok=1.0,
        output_per_mtok=5.0,
        size="small",
        effort=None,  # Haiku 4.5 does not support the effort parameter
        notes="Extended thinking is manual on Haiku 4.5 and left off here.",
    ),
    "claude-opus-5": ModelSpec(
        key="claude-opus-5",
        provider="anthropic",
        model_id="claude-opus-5",
        input_per_mtok=5.0,
        output_per_mtok=25.0,
        size="large",
        effort="low",
        notes="Adaptive thinking is on by default; effort=low keeps it short. Thinking tokens bill as output.",
    ),
    # ---- OpenAI ---------------------------------------------------------
    "gpt-5.6-luna": ModelSpec(
        key="gpt-5.6-luna",
        provider="openai",
        model_id="gpt-5.6-luna",
        input_per_mtok=0.20,
        output_per_mtok=1.20,
        size="small",
        effort="low",
    ),
    "gpt-5.6-sol": ModelSpec(
        key="gpt-5.6-sol",
        provider="openai",
        model_id="gpt-5.6-sol",
        input_per_mtok=4.0,
        output_per_mtok=20.0,
        size="large",
        effort="low",
        notes="Promotional pricing through at least 2026-11-21.",
    ),
    # ---- Google ---------------------------------------------------------
    "gemini-3.8-flash": ModelSpec(
        key="gemini-3.8-flash",
        provider="gemini",
        model_id="gemini-3.8-flash",
        input_per_mtok=0.75,
        output_per_mtok=3.75,
        size="small",
        effort="low",
        notes="Promo price through 2026-12-31 ($1.50/$7.50 after). Output price includes thinking tokens.",
    ),
    "gemini-3.1-pro": ModelSpec(
        key="gemini-3.1-pro",
        provider="gemini",
        model_id="gemini-3.1-pro-preview",
        input_per_mtok=2.0,
        output_per_mtok=12.0,
        size="large",
        effort="low",
        notes="Thinking cannot be disabled on 3.1 Pro; 'low' is the floor.",
    ),
    # ---- Test double ----------------------------------------------------
    "mock": ModelSpec(
        key="mock",
        provider="mock",
        model_id="mock-classifier",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        notes="Deterministic keyword classifier for testing the pipeline without API keys.",
    ),
}

# The default comparison set: Jev vs a small and a large model from each vendor.
DEFAULT_ROSTER = [
    "jev",
    "claude-haiku-4.5",
    "claude-opus-5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gemini-3.8-flash",
    "gemini-3.1-pro",
]

ENV_KEYS: dict[Provider, str] = {
    "typesafe": "TYPESAFE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mock": "",
}


def resolve_models(keys: list[str] | None) -> list[ModelSpec]:
    if not keys:
        keys = DEFAULT_ROSTER
    out = []
    for k in keys:
        k = k.strip()
        if k == "all":
            out.extend(MODELS[x] for x in DEFAULT_ROSTER)
            continue
        if k not in MODELS:
            raise KeyError(f"Unknown model key {k!r}. Known: {', '.join(MODELS)}")
        out.append(MODELS[k])
    return out

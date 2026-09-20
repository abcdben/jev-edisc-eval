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

Provider = Literal["typesafe", "laya", "ollama", "lexical", "anthropic", "openai", "gemini", "mock"]


@dataclass(frozen=True)
class ModelSpec:
    key: str  # short name used on the CLI
    provider: Provider
    model_id: str  # what gets sent on the wire
    input_per_mtok: float
    output_per_mtok: float
    size: Literal["small", "mid", "large", "n/a"] = "n/a"
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
    # ---- ConvAI Laya (local System 1; same Noul/Choice/Score surface as Jev) ----
    "laya": ModelSpec(
        key="laya",
        provider="laya",
        model_id="convaiinnovations/laya",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        size="n/a",
        notes="Self-hosted English checkpoint (ModernBERT-large, 512 ctx). $0. Zero-shot; they say fine-tuning is where most quality comes from.",
    ),
    "laya-typed": ModelSpec(
        key="laya-typed",
        provider="laya",
        model_id="convaiinnovations/laya",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        size="n/a",
        extra={"subfolder": "typed-decisions"},
        notes="Self-hosted typed-decisions checkpoint (1024 ctx). Fine-tuned on invoice/security/CS/agent-trace, not eDiscovery.",
    ),
    "laya-multilingual": ModelSpec(
        key="laya-multilingual",
        provider="laya",
        model_id="convaiinnovations/laya",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        size="n/a",
        extra={"subfolder": "multilingual"},
        notes="Self-hosted multilingual checkpoint (mmBERT-base, 322M, 1024 ctx). Smaller model, 2x the document window.",
    ),
    "laya-ft-veridian": ModelSpec(
        key="laya-ft-veridian",
        provider="laya",
        model_id="models/laya-ft-veridian",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        size="n/a",
        notes="SUPERVISED. English checkpoint fine-tuned (RLCD recipe, 1024 ctx) on the Veridian dev split. Evaluate on data/veridian/ft_test.jsonl only.",
    ),
    "laya-ft-mnk": ModelSpec(
        key="laya-ft-mnk",
        provider="laya",
        model_id="models/laya-ft-mnk",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        size="n/a",
        notes="SUPERVISED. English checkpoint fine-tuned (RLCD recipe, 1024 ctx) on the Mallinckrodt dev split. Evaluate on data/mallinckrodt/ft_test.jsonl only.",
    ),
    # ---- SMALL tier: the cheapest model each vendor sells ---------------
    "claude-haiku-4.5": ModelSpec(
        key="claude-haiku-4.5",
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        input_per_mtok=1.0,
        output_per_mtok=5.0,
        size="small",
        effort=None,  # Haiku 4.5 has no effort parameter; thinking is off unless requested
        notes="Floor == default: no thinking.",
    ),
    "gpt-5.6-luna": ModelSpec(
        key="gpt-5.6-luna",
        provider="openai",
        model_id="gpt-5.6-luna",
        input_per_mtok=0.20,
        output_per_mtok=1.20,
        size="small",
        effort="none",
        notes="Floor: reasoning.effort=none. Vendor default is medium.",
    ),
    "gemini-3.5-flash-lite": ModelSpec(
        key="gemini-3.5-flash-lite",
        provider="gemini",
        model_id="gemini-3.5-flash-lite",
        input_per_mtok=0.30,
        output_per_mtok=2.50,
        size="small",
        effort="minimal",
        notes="Floor: thinking_level=minimal (also the vendor default). Output price includes thinking tokens.",
    ),
    # ---- MID tier: what teams actually deploy for classification -------
    "claude-sonnet-5": ModelSpec(
        key="claude-sonnet-5",
        provider="anthropic",
        model_id="claude-sonnet-5",
        input_per_mtok=2.0,
        output_per_mtok=10.0,
        size="mid",
        effort="low",
        extra={"thinking": {"type": "disabled"}},
        notes="Floor: thinking disabled + effort=low. Vendor default is adaptive thinking at effort=high.",
    ),
    "gpt-5.6-terra": ModelSpec(
        key="gpt-5.6-terra",
        provider="openai",
        model_id="gpt-5.6-terra",
        input_per_mtok=2.0,
        output_per_mtok=12.0,
        size="mid",
        effort="none",
        notes="Floor: reasoning.effort=none. Vendor default is medium.",
    ),
    "gemini-3.8-flash": ModelSpec(
        key="gemini-3.8-flash",
        provider="gemini",
        model_id="gemini-3.8-flash",
        input_per_mtok=0.75,
        output_per_mtok=3.75,
        size="mid",
        effort="low",
        notes="Floor: thinking_level=low (minimal not supported on 3.8 Flash). Vendor default is medium. Promo price through 2026-12-31.",
    ),
    # ---- LARGE tier: defined but NOT in the default roster (cost) -------
    "claude-opus-5": ModelSpec(
        key="claude-opus-5",
        provider="anthropic",
        model_id="claude-opus-5",
        input_per_mtok=5.0,
        output_per_mtok=25.0,
        size="large",
        effort="low",
        extra={"thinking": {"type": "disabled"}},
        notes="Excluded from default roster 2026-09-19 (cost). Available with -m.",
    ),
    "gpt-5.6-sol": ModelSpec(
        key="gpt-5.6-sol",
        provider="openai",
        model_id="gpt-5.6-sol",
        input_per_mtok=4.0,
        output_per_mtok=20.0,
        size="large",
        effort="none",
        notes="Excluded from default roster 2026-09-19 (cost). Available with -m.",
    ),
    "gemini-3.1-pro": ModelSpec(
        key="gemini-3.1-pro",
        provider="gemini",
        model_id="gemini-3.1-pro-preview",
        input_per_mtok=2.0,
        output_per_mtok=12.0,
        size="large",
        effort="low",
        notes="Excluded from default roster 2026-09-19. Thinking cannot be disabled; 'low' is the floor.",
    ),
    # ---- Floors / negative controls (local, $0) ---------------------------
    "lexical": ModelSpec(
        key="lexical",
        provider="lexical",
        model_id="lexical-terms",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        notes="Keyword-overlap baseline built from the request text. No model. If this is close to the models, the set is too easy.",
    ),
    "gemma3-12b": ModelSpec(
        key="gemma3-12b",
        provider="ollama",
        model_id="gemma3:12b",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        size="small",
        extra={"num_ctx": 8192},
        notes="Local open model via Ollama on this Mac. Same prompt/schema as the cloud LLMs; temperature 0; no thinking.",
    ),
    "qwen3-14b": ModelSpec(
        key="qwen3-14b",
        provider="ollama",
        model_id="qwen3:14b",
        input_per_mtok=0.0,
        output_per_mtok=0.0,
        size="small",
        extra={"num_ctx": 8192, "think": False},
        notes="Local open model via Ollama; thinking disabled. Optional second local floor.",
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

# The default comparison set: Jev vs the small and mid tier from each vendor.
SMALL_TIER = ["claude-haiku-4.5", "gpt-5.6-luna", "gemini-3.5-flash-lite"]
MID_TIER = ["claude-sonnet-5", "gpt-5.6-terra", "gemini-3.8-flash"]
DEFAULT_ROSTER = ["jev", *SMALL_TIER, *MID_TIER]

# Vendor-default effort settings, used by the effort pilot (`--effort default`).
# None means "send no effort/thinking parameters at all".
VENDOR_DEFAULT_EFFORT: dict[str, str | None] = {
    "claude-haiku-4.5": None,
    "gpt-5.6-luna": "medium",
    "gemini-3.5-flash-lite": "minimal",
    "claude-sonnet-5": "high",
    "gpt-5.6-terra": "medium",
    "gemini-3.8-flash": "medium",
}

ENV_KEYS: dict[Provider, str] = {
    "typesafe": "TYPESAFE_API_KEY",
    "laya": "",
    "ollama": "",
    "lexical": "",
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
        if k == "small":
            out.extend(MODELS[x] for x in SMALL_TIER)
            continue
        if k == "mid":
            out.extend(MODELS[x] for x in MID_TIER)
            continue
        if k not in MODELS:
            raise KeyError(f"Unknown model key {k!r}. Known: {', '.join(MODELS)}")
        out.append(MODELS[k])
    return out

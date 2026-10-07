from __future__ import annotations

from dataclasses import replace

from ..config import MODELS, VENDOR_DEFAULT_EFFORT, ModelSpec
from .base import Prediction, Provider, RawResult


def parse_model_key(key: str) -> tuple[ModelSpec, str | None]:
    """'gpt-5.6-luna' -> (spec, None); 'jev@choice' -> (jev spec, 'choice')."""
    if "@" in key:
        base, variant = key.split("@", 1)
        return MODELS[base], variant
    return MODELS[key], None


def make_provider(
    key: str,
    effort_override: str | None = None,
    phrasing: str = "rfp",
    batch: bool = False,
    flex: bool = True,
    temperature: float | None = None,
) -> Provider:
    spec, variant = parse_model_key(key)
    if effort_override and spec.provider not in ("typesafe", "laya", "ollama", "lexical", "mock"):
        if effort_override == "default":
            spec = replace(spec, effort=VENDOR_DEFAULT_EFFORT.get(spec.key), extra={})
        else:
            spec = replace(spec, effort=effort_override, extra={})
    if temperature is not None and spec.provider in ("anthropic", "openai", "gemini"):
        # all three providers splat spec.extra into the request
        spec = replace(spec, extra={**spec.extra, "temperature": temperature})

    if spec.provider == "typesafe":
        from .typesafe import TypeSafeProvider

        return TypeSafeProvider(spec, variant=variant or "base")
    if spec.provider == "laya":
        from .laya_ import LayaProvider

        return LayaProvider(spec, variant=variant or "base")
    if spec.provider == "ollama":
        from .ollama_ import OllamaProvider

        return OllamaProvider(spec, phrasing=phrasing)
    if spec.provider == "lexical":
        from .lexical import LexicalProvider

        return LexicalProvider(spec)
    if spec.provider == "anthropic":
        from .anthropic_ import AnthropicProvider

        return AnthropicProvider(spec, phrasing=phrasing, batch=batch)
    if spec.provider == "openai":
        from .openai_ import OpenAIProvider

        return OpenAIProvider(spec, phrasing=phrasing, flex=flex)
    if spec.provider == "openai_decisions":
        from .openai_decisions import OpenAIDecisionsProvider

        return OpenAIDecisionsProvider(spec, variant=variant)
    if spec.provider == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider(spec, phrasing=phrasing)
    if spec.provider == "mock":
        from .mock import MockProvider

        return MockProvider(spec)
    raise ValueError(f"unknown provider {spec.provider}")


__all__ = ["Prediction", "Provider", "RawResult", "make_provider", "parse_model_key"]

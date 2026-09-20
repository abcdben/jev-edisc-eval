from __future__ import annotations

from ..config import ModelSpec
from .base import Prediction, Provider


def make_provider(spec: ModelSpec, effort_override: str | None = None) -> Provider:
    if effort_override and spec.provider not in ("typesafe", "mock"):
        # dataclass is frozen; build a modified copy
        from dataclasses import replace

        from ..config import VENDOR_DEFAULT_EFFORT

        if effort_override == "default":
            # Vendor default: drop our floor settings (effort + thinking-disabled) entirely.
            spec = replace(spec, effort=VENDOR_DEFAULT_EFFORT.get(spec.key), extra={})
        else:
            spec = replace(spec, effort=effort_override, extra={})

    if spec.provider == "typesafe":
        from .typesafe import TypeSafeProvider

        return TypeSafeProvider(spec)
    if spec.provider == "anthropic":
        from .anthropic_ import AnthropicProvider

        return AnthropicProvider(spec)
    if spec.provider == "openai":
        from .openai_ import OpenAIProvider

        return OpenAIProvider(spec)
    if spec.provider == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider(spec)
    if spec.provider == "mock":
        from .mock import MockProvider

        return MockProvider(spec)
    raise ValueError(f"unknown provider {spec.provider}")


__all__ = ["Prediction", "Provider", "make_provider"]

"""Centralized LLM configuration, resolved from environment variables.

All credentials and tunables live here so that no business-logic module ever
reads ``os.environ`` directly. This keeps the call to the model decoupled from
the rest of the code and makes the runtime mode (real vs. mock) explicit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional: load a local .env if python-dotenv is available
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience, not a hard dep
    pass


PROVIDER_OPENAI = "openai"
PROVIDER_MOCK = "mock"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class LLMConfig:
    """Immutable snapshot of the LLM runtime configuration."""

    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    temperature: float
    max_tokens: int
    max_retries: int
    allow_fallback: bool
    log_level: str

    @property
    def is_mock(self) -> bool:
        return self.provider == PROVIDER_MOCK

    def describe(self) -> str:
        """Human-readable one-liner for logs and report headers (no secrets)."""
        if self.is_mock:
            return "provider=mock (deterministic, no API key required)"
        return f"provider=openai model={self.model} fallback={self.allow_fallback}"


def resolve_provider(explicit: str | None, api_key: str | None) -> str:
    """Decide which provider to use.

    Precedence:
      1. An explicit ``LLM_PROVIDER`` value always wins.
      2. Otherwise, if an OpenAI API key is present, use the real provider.
      3. Otherwise, fall back to the mock provider so the demo is reproducible
         with zero credentials.
    """
    if explicit:
        value = explicit.strip().lower()
        if value in {PROVIDER_OPENAI, PROVIDER_MOCK}:
            return value
        raise ValueError(
            f"Unknown LLM_PROVIDER={explicit!r}. "
            f"Use '{PROVIDER_OPENAI}' or '{PROVIDER_MOCK}'."
        )
    if api_key:
        return PROVIDER_OPENAI
    return PROVIDER_MOCK


def load_config() -> LLMConfig:
    """Build an :class:`LLMConfig` from the current environment."""
    api_key = os.getenv("OPENAI_API_KEY") or None
    provider = resolve_provider(os.getenv("LLM_PROVIDER"), api_key)
    return LLMConfig(
        provider=provider,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=_env_float("LLM_TEMPERATURE", 0.2),
        max_tokens=_env_int("LLM_MAX_TOKENS", 2000),
        max_retries=_env_int("LLM_MAX_RETRIES", 2),
        allow_fallback=_env_bool("LLM_ALLOW_FALLBACK", True),
        log_level=os.getenv("LLM_LOG_LEVEL", "INFO"),
    )

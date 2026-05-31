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


PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"

# Default model per provider, used when no model env var is set.
# gemini-2.5-flash is the broadly-available free-tier model; thinking is disabled
# in the provider so the full JSON answer fits the token budget.
_DEFAULT_MODELS = {
    PROVIDER_GEMINI: "gemini-2.5-flash",
    PROVIDER_OPENAI: "gpt-4o-mini",
}


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
    log_level: str

    def describe(self) -> str:
        """Human-readable one-liner for logs and report headers (no secrets)."""
        return f"provider={self.provider} model={self.model}"


class MissingAPIKeyError(RuntimeError):
    """Raised when no LLM API key is configured. Generative AI is mandatory."""


def resolve_provider(
    explicit: str | None,
    gemini_key: str | None,
    openai_key: str | None,
) -> str:
    """Decide which real provider to use.

    Precedence:
      1. An explicit ``LLM_PROVIDER`` value always wins.
      2. Otherwise, if a Gemini key is present, use Gemini (default - free tier).
      3. Otherwise, if an OpenAI key is present, use OpenAI.
      4. Otherwise raise: generative AI is mandatory, there is no offline mode.
    """
    if explicit:
        value = explicit.strip().lower()
        if value in {PROVIDER_GEMINI, PROVIDER_OPENAI}:
            return value
        raise ValueError(
            f"Unknown LLM_PROVIDER={explicit!r}. "
            f"Use '{PROVIDER_GEMINI}' or '{PROVIDER_OPENAI}'."
        )
    if gemini_key:
        return PROVIDER_GEMINI
    if openai_key:
        return PROVIDER_OPENAI
    raise MissingAPIKeyError(
        "No LLM API key found. This solution requires real generative AI: set "
        "GEMINI_API_KEY (free tier at https://aistudio.google.com/apikey) or "
        "OPENAI_API_KEY in your environment / .env file."
    )


def _api_key_for(provider: str, gemini_key: str | None, openai_key: str | None) -> str | None:
    if provider == PROVIDER_GEMINI:
        return gemini_key
    if provider == PROVIDER_OPENAI:
        return openai_key
    return None


def _model_for(provider: str) -> str:
    """Resolve the model name, honoring an explicit env var per provider."""
    if provider == PROVIDER_GEMINI:
        return os.getenv("GEMINI_MODEL") or _DEFAULT_MODELS[PROVIDER_GEMINI]
    return os.getenv("OPENAI_MODEL") or _DEFAULT_MODELS[PROVIDER_OPENAI]


def load_config() -> LLMConfig:
    """Build an :class:`LLMConfig` from the current environment.

    Raises :class:`MissingAPIKeyError` if no provider key is configured.
    """
    # GOOGLE_API_KEY is the variable the google-genai SDK reads by default; we
    # accept either it or GEMINI_API_KEY for convenience.
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or None
    openai_key = os.getenv("OPENAI_API_KEY") or None
    provider = resolve_provider(os.getenv("LLM_PROVIDER"), gemini_key, openai_key)
    return LLMConfig(
        provider=provider,
        model=_model_for(provider),
        api_key=_api_key_for(provider, gemini_key, openai_key),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=_env_float("LLM_TEMPERATURE", 0.2),
        max_tokens=_env_int("LLM_MAX_TOKENS", 8000),
        max_retries=_env_int("LLM_MAX_RETRIES", 4),
        log_level=os.getenv("LLM_LOG_LEVEL", "INFO"),
    )

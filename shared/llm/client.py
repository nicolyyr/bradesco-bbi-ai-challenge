"""High-level LLM client used by the business logic of both cases.

Responsibilities:
  * pick the provider (real OpenAI or deterministic mock) from config;
  * render the prompt, call the model, and parse the JSON answer;
  * validate the answer against a pydantic schema (the output contract);
  * on any failure (call error, invalid JSON, schema mismatch) fall back to a
    deterministic baseline so the pipeline always produces a usable result;
  * report which path produced the answer (``source`` metadata) so a demo can
    prove the LLM was actually used.

Business modules call :meth:`LLMClient.generate_structured` and get back a
validated pydantic model plus a :class:`GenerationResult` describing how it was
produced. They never touch the SDK or parse JSON themselves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .config import PROVIDER_GEMINI, PROVIDER_OPENAI, LLMConfig, load_config
from .logging_utils import get_logger
from .providers import (
    GeminiProvider,
    LLMError,
    LLMProvider,
    LLMResponse,
    MockProvider,
    OpenAIProvider,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

SOURCE_LLM = "llm"
SOURCE_MOCK = "mock"
SOURCE_FALLBACK = "fallback"


@dataclass
class GenerationResult:
    """Outcome of a structured generation, with provenance for demos/tests."""

    data: BaseModel
    source: str  # one of SOURCE_LLM / SOURCE_MOCK / SOURCE_FALLBACK
    provider: str
    model: str
    attempts: int
    latency_ms: float
    used_fallback: bool

    def banner(self) -> str:
        if self.source == SOURCE_LLM:
            return f"[LLM] {self.provider}:{self.model} ({self.attempts} attempt(s), {self.latency_ms:.0f} ms)"
        if self.source == SOURCE_MOCK:
            return "[MOCK] deterministic baseline (no API key / LLM_PROVIDER=mock)"
        return f"[FALLBACK] deterministic baseline used after LLM failure ({self.provider}:{self.model})"


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from a model response.

    Handles the common cases of a bare JSON object and a JSON object wrapped in
    Markdown code fences. Raises ``ValueError`` if no object can be parsed.
    """
    if not text or not text.strip():
        raise ValueError("empty response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # strip ```json ... ``` or ``` ... ``` fences
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise ValueError("no JSON object found in response")


class LLMClient:
    """Orchestrates a structured generation with validation and fallback."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        provider: LLMProvider | None = None,
        baseline_fn: Callable[[str, str], dict] | None = None,
    ) -> None:
        self.config = config or load_config()
        self._baseline_fn = baseline_fn
        if provider is not None:
            self.provider = provider
        elif self.config.is_mock:
            if baseline_fn is None:
                raise ValueError(
                    "Mock provider requires a baseline_fn to derive output from input."
                )
            self.provider = MockProvider(self.config, baseline_fn)
        elif self.config.provider == PROVIDER_GEMINI:
            self.provider = GeminiProvider(self.config)
        elif self.config.provider == PROVIDER_OPENAI:
            self.provider = OpenAIProvider(self.config)
        else:  # pragma: no cover - resolve_provider guards against this
            raise ValueError(f"Unsupported provider: {self.config.provider!r}")
        logger.info("LLMClient ready: %s", self.config.describe())

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        fallback_payload: dict | None = None,
    ) -> GenerationResult:
        """Call the model and return a validated ``schema`` instance.

        Parameters
        ----------
        system_prompt, user_prompt:
            The rendered prompts.
        schema:
            A pydantic model describing the expected output contract.
        fallback_payload:
            A deterministic, schema-compatible dict to use if the LLM path
            fails. Required when fallback is enabled and the provider is real.
        """
        try:
            response = self.provider.complete(system_prompt, user_prompt)
            data = self._parse_and_validate(response, schema)
            source = SOURCE_MOCK if self.provider.name == "mock" else SOURCE_LLM
            return GenerationResult(
                data=data,
                source=source,
                provider=response.provider,
                model=response.model,
                attempts=response.attempts,
                latency_ms=response.latency_ms,
                used_fallback=False,
            )
        except (LLMError, ValueError, ValidationError) as exc:
            logger.warning("Structured generation failed: %s", exc)
            if not self.config.allow_fallback or fallback_payload is None:
                raise
            logger.warning(
                "Falling back to deterministic baseline (LLM_ALLOW_FALLBACK=true)."
            )
            data = schema.model_validate(fallback_payload)
            return GenerationResult(
                data=data,
                source=SOURCE_FALLBACK,
                provider=self.provider.name,
                model=getattr(self.config, "model", "unknown"),
                attempts=0,
                latency_ms=0.0,
                used_fallback=True,
            )

    def _parse_and_validate(self, response: LLMResponse, schema: Type[T]) -> T:
        payload = _extract_json(response.text)
        return schema.model_validate(payload)

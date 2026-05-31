"""High-level LLM client used by the business logic of both cases.

Responsibilities:
  * pick the real provider (Gemini or OpenAI) from config;
  * render the prompt, call the model, and parse the JSON answer;
  * validate the answer against a pydantic schema (the output contract),
    regenerating a few times if the model returns malformed/invalid JSON;
  * report which model produced the answer (``source`` metadata) so a demo can
    prove generative AI was actually used.

Generative AI is mandatory: there is no mock/offline path and no deterministic
fallback. If the model cannot produce a schema-valid answer after retries, the
call raises rather than silently degrading.

Business modules call :meth:`LLMClient.generate_structured` and get back a
validated pydantic model plus a :class:`GenerationResult`. They never touch the
SDK or parse JSON themselves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from .config import PROVIDER_GEMINI, PROVIDER_OPENAI, LLMConfig, load_config
from .logging_utils import get_logger
from .providers import (
    GeminiProvider,
    LLMError,
    LLMProvider,
    LLMResponse,
    OpenAIProvider,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

SOURCE_LLM = "llm"


@dataclass
class GenerationResult:
    """Outcome of a structured generation, with provenance for demos/tests."""

    data: BaseModel
    # Provenance of the answer. Always SOURCE_LLM today (generative AI is the
    # only path); kept as an explicit field so the banner/logs can distinguish
    # sources if a second one (e.g. a cache) is ever added.
    source: str
    provider: str
    model: str
    attempts: int
    latency_ms: float

    def banner(self) -> str:
        return (
            f"[LLM] {self.provider}:{self.model} "
            f"({self.attempts} attempt(s), {self.latency_ms:.0f} ms)"
        )


def _sanitize_json_text(s: str) -> str:
    """Remove raw control characters that models occasionally emit inside string
    values (e.g. unescaped newlines/tabs in a verbatim quote), which break
    json.loads with 'Expecting , delimiter'. Preserves already-escaped sequences.
    """
    # Strip ASCII control chars except whitespace that JSON tolerates between
    # tokens; inside strings these are illegal, so removing them is the safe fix.
    return "".join(ch for ch in s if ch >= " " or ch in "\r\n\t").replace("\t", " ")


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from a model response.

    Handles a bare JSON object, a JSON object wrapped in Markdown code fences,
    and objects polluted with raw control characters. Raises ``ValueError`` if no
    object can be parsed.
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

    # narrow to the outermost object if there is surrounding prose
    start, end = cleaned.find("{"), cleaned.rfind("}")
    candidate = cleaned[start : end + 1] if (start != -1 and end > start) else cleaned

    for attempt in (candidate, _sanitize_json_text(candidate)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    raise ValueError("could not parse a JSON object from the model response")


class LLMClient:
    """Orchestrates a structured generation against a real LLM provider."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self.config = config or load_config()
        if provider is not None:
            self.provider = provider
        elif self.config.provider == PROVIDER_GEMINI:
            self.provider = GeminiProvider(self.config)
        elif self.config.provider == PROVIDER_OPENAI:
            self.provider = OpenAIProvider(self.config)
        else:  # pragma: no cover - resolve_provider guards against this
            raise ValueError(f"Unsupported provider: {self.config.provider!r}")
        logger.info("LLMClient ready: %s", self.config.describe())

    # Number of full regenerations on a parse/validation failure before raising.
    REGEN_ATTEMPTS = 3

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
    ) -> GenerationResult:
        """Call the model and return a validated ``schema`` instance.

        Parameters
        ----------
        system_prompt, user_prompt:
            The rendered prompts.
        schema:
            A pydantic model describing the expected output contract. It is also
            passed to providers that support native structured output (Gemini),
            constraining decoding to a guaranteed-valid JSON shape.

        Raises
        ------
        LLMError / ValueError / ValidationError
            If the model cannot produce a schema-valid answer after retries.
            There is no deterministic fallback: generative AI is mandatory.
        """
        # A model can occasionally emit malformed JSON (e.g. an unescaped char in
        # a long verbatim quote). Since that is intermittent, regenerate a few
        # times before giving up.
        last_exc: Exception | None = None
        for gen in range(1, self.REGEN_ATTEMPTS + 1):
            try:
                response = self.provider.complete(
                    system_prompt, user_prompt, response_schema=schema
                )
                data = self._parse_and_validate(response, schema)
                return GenerationResult(
                    data=data,
                    source=SOURCE_LLM,
                    provider=response.provider,
                    model=response.model,
                    attempts=response.attempts,
                    latency_ms=response.latency_ms,
                )
            except (LLMError, ValueError, ValidationError) as exc:
                last_exc = exc
                logger.warning(
                    "Structured generation attempt %s/%s failed: %s",
                    gen, self.REGEN_ATTEMPTS, exc,
                )

        raise last_exc  # type: ignore[misc]

    def _parse_and_validate(self, response: LLMResponse, schema: Type[T]) -> T:
        payload = _extract_json(response.text)
        return schema.model_validate(payload)

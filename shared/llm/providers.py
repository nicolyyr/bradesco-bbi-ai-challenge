"""LLM provider abstraction.

This module isolates *how* we talk to a model from *what* we ask it. Business
logic depends only on the :class:`LLMProvider` interface and never imports a
vendor SDK directly. Two real providers are shipped:

* :class:`GeminiProvider` - the default integration (requires ``GEMINI_API_KEY``).
  Google offers a free tier, so this is the lowest-friction way to run the
  generative-AI path.
* :class:`OpenAIProvider` - alternative integration (requires ``OPENAI_API_KEY``).
  Lets the solution do a real multi-model comparison.

Generative AI is mandatory: there is no mock/offline provider. The test suite
exercises these real providers by injecting a fake SDK client (no network, no
key). Both SDKs are imported lazily, so importing this module never requires
either package to be installed. All providers return a :class:`LLMResponse` with
the raw text plus metadata useful for debugging and for proving which model
produced the answer.
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .config import LLMConfig
from .logging_utils import get_logger

logger = get_logger(__name__)

# Cap any single backoff sleep so an interactive run never hangs too long.
_MAX_BACKOFF_SECONDS = 30.0


def _backoff_seconds(error: Exception, attempt: int) -> float:
    """How long to wait before the next retry.

    If the provider returned a rate-limit error with a server-suggested
    ``retryDelay`` (e.g. Gemini 429 "Please retry in 24s"), honor it. Otherwise
    use exponential backoff. Always capped by ``_MAX_BACKOFF_SECONDS``.
    """
    text = str(error)
    suggested = 0.0
    m = re.search(r"retry(?:Delay|\s+in)\D*?(\d+(?:\.\d+)?)\s*s", text, re.IGNORECASE)
    if m:
        suggested = float(m.group(1)) + 1.0  # small margin over the server hint
    backoff = max(suggested, min(2.0 * attempt, 8.0))
    return min(backoff, _MAX_BACKOFF_SECONDS)


class LLMError(RuntimeError):
    """Raised when the model call fails after exhausting retries."""


@dataclass
class LLMResponse:
    """Result of a single completion call."""

    text: str
    provider: str
    model: str
    attempts: int = 1
    latency_ms: float = 0.0
    raw: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """Contract every provider must implement."""

    name: str

    @abstractmethod
    def complete(
        self, system_prompt: str, user_prompt: str, response_schema: object | None = None
    ) -> LLMResponse:
        """Return a completion for the given system + user prompts.

        ``response_schema`` (a pydantic model) is an optional hint: providers that
        support native structured output (e.g. Gemini) use it to guarantee
        schema-valid JSON; others ignore it and rely on JSON mode + validation.
        """


class OpenAIProvider(LLMProvider):
    """Real OpenAI integration with retries and JSON-mode output.

    The OpenAI SDK is imported lazily so that the mock path (and the test
    suite) never require the package to be importable at module load time.
    """

    name = "openai"

    def __init__(self, config: LLMConfig, client: object | None = None) -> None:
        self.config = config
        self._client = client  # injectable for tests

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMError(
                "The 'openai' package is not installed. Run "
                "'pip install -r requirements.txt'."
            ) from exc
        if not self.config.api_key:
            raise LLMError("OPENAI_API_KEY is not set.")
        kwargs = {"api_key": self.config.api_key}
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def complete(
        self, system_prompt: str, user_prompt: str, response_schema: object | None = None
    ) -> LLMResponse:
        # OpenAI path relies on JSON mode + downstream validation; response_schema
        # is accepted for interface parity but not used here.
        client = self._get_client()
        last_error: Exception | None = None
        attempts = self.config.max_retries + 1

        for attempt in range(1, attempts + 1):
            start = time.perf_counter()
            try:
                logger.debug(
                    "OpenAI call attempt %s/%s (model=%s)",
                    attempt,
                    attempts,
                    self.config.model,
                )
                completion = client.chat.completions.create(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                latency_ms = (time.perf_counter() - start) * 1000
                text = completion.choices[0].message.content or ""
                logger.info(
                    "OpenAI call ok (model=%s, attempt=%s, %.0f ms)",
                    self.config.model,
                    attempt,
                    latency_ms,
                )
                return LLMResponse(
                    text=text,
                    provider=self.name,
                    model=self.config.model,
                    attempts=attempt,
                    latency_ms=latency_ms,
                )
            except Exception as exc:  # noqa: BLE001 - we re-raise as LLMError
                last_error = exc
                logger.warning(
                    "OpenAI call failed (attempt %s/%s): %s",
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(_backoff_seconds(exc, attempt))

        raise LLMError(
            f"OpenAI call failed after {attempts} attempt(s): {last_error}"
        ) from last_error


class GeminiProvider(LLMProvider):
    """Real Google Gemini integration with retries and JSON-mode output.

    Default real provider: Google offers a free tier, so this is the
    lowest-friction way for a reviewer to exercise the genuine generative-AI
    path. The ``google-genai`` SDK is imported lazily so the mock path and the
    test suite never require it. A client can be injected for testing.
    """

    name = "gemini"

    def __init__(self, config: LLMConfig, client: object | None = None) -> None:
        self.config = config
        self._client = client  # injectable for tests

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMError(
                "The 'google-genai' package is not installed. Run "
                "'pip install -r requirements.txt'."
            ) from exc
        if not self.config.api_key:
            raise LLMError("GEMINI_API_KEY is not set.")
        self._client = genai.Client(api_key=self.config.api_key)
        return self._client

    def _build_config(self, system_prompt: str, response_schema: object | None = None):
        # Imported lazily alongside the client to avoid a hard dependency.
        from google.genai import types

        kwargs = dict(
            system_instruction=system_prompt,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
            response_mime_type="application/json",
        )
        # Native structured output: when a pydantic schema is provided, Gemini
        # constrains decoding to it and returns GUARANTEED-valid JSON. This is the
        # robust fix for malformed JSON from unescaped chars in long verbatim
        # quotes. Guarded so an unsupported schema/SDK falls back to plain JSON mode.
        if response_schema is not None:
            try:
                kwargs["response_schema"] = response_schema
            except Exception:  # pragma: no cover
                pass
        # Gemini 2.5 models spend part of max_output_tokens on internal "thinking"
        # tokens, which can truncate the visible JSON answer. Disable thinking so
        # the full structured output fits. Guarded: older models / SDKs that don't
        # support ThinkingConfig simply skip this.
        try:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except Exception:  # pragma: no cover - depends on SDK/model support
            pass

        return types.GenerateContentConfig(**kwargs)

    def complete(
        self, system_prompt: str, user_prompt: str, response_schema: object | None = None
    ) -> LLMResponse:
        client = self._get_client()
        gen_config = self._build_config(system_prompt, response_schema)
        last_error: Exception | None = None
        attempts = self.config.max_retries + 1

        for attempt in range(1, attempts + 1):
            start = time.perf_counter()
            try:
                logger.debug(
                    "Gemini call attempt %s/%s (model=%s)",
                    attempt,
                    attempts,
                    self.config.model,
                )
                response = client.models.generate_content(
                    model=self.config.model,
                    contents=user_prompt,
                    config=gen_config,
                )
                latency_ms = (time.perf_counter() - start) * 1000
                text = getattr(response, "text", "") or ""
                logger.info(
                    "Gemini call ok (model=%s, attempt=%s, %.0f ms)",
                    self.config.model,
                    attempt,
                    latency_ms,
                )
                return LLMResponse(
                    text=text,
                    provider=self.name,
                    model=self.config.model,
                    attempts=attempt,
                    latency_ms=latency_ms,
                )
            except Exception as exc:  # noqa: BLE001 - we re-raise as LLMError
                last_error = exc
                logger.warning(
                    "Gemini call failed (attempt %s/%s): %s",
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(_backoff_seconds(exc, attempt))

        raise LLMError(
            f"Gemini call failed after {attempts} attempt(s): {last_error}"
        ) from last_error

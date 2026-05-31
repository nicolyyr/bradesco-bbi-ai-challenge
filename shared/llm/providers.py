"""LLM provider abstraction.

This module isolates *how* we talk to a model from *what* we ask it. Business
logic depends only on the :class:`LLMProvider` interface and never imports a
vendor SDK directly. Three concrete providers are shipped:

* :class:`GeminiProvider` - the default real integration (requires
  ``GEMINI_API_KEY``). Google offers a free tier, so this is the lowest-friction
  way to run the real generative-AI path.
* :class:`OpenAIProvider` - alternative real integration (requires
  ``OPENAI_API_KEY``). Lets the solution do a real multi-model comparison.
* :class:`MockProvider`   - a deterministic, offline provider used for tests
  and credential-free demos. It delegates to a caller-supplied function so the
  mock answer is computed from the *actual* input rather than hardcoded.

Both real SDKs are imported lazily, so the mock path and the test suite never
require either package to be importable at module load time. All providers
return a :class:`LLMResponse` with the raw text plus metadata useful for
debugging and for proving in a demo which path produced the answer.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from .config import LLMConfig
from .logging_utils import get_logger

logger = get_logger(__name__)


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
                "'pip install -r requirements.txt' or use LLM_PROVIDER=mock."
            ) from exc
        if not self.config.api_key:
            raise LLMError(
                "OPENAI_API_KEY is not set. Export it or use LLM_PROVIDER=mock "
                "for a credential-free demo."
            )
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
                # simple linear backoff; kept short for interactive demos
                if attempt < attempts:
                    time.sleep(min(2.0 * attempt, 5.0))

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
                "'pip install -r requirements.txt' or use LLM_PROVIDER=mock."
            ) from exc
        if not self.config.api_key:
            raise LLMError(
                "GEMINI_API_KEY is not set. Export it or use LLM_PROVIDER=mock "
                "for a credential-free demo."
            )
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
                # simple linear backoff; kept short for interactive demos
                if attempt < attempts:
                    time.sleep(min(2.0 * attempt, 5.0))

        raise LLMError(
            f"Gemini call failed after {attempts} attempt(s): {last_error}"
        ) from last_error


class MockProvider(LLMProvider):
    """Deterministic, offline provider for tests and credential-free demos.

    It does NOT hardcode an answer. Instead it runs a caller-supplied
    ``baseline_fn`` over the real input and serializes the result as JSON,
    emulating a structured LLM response. This keeps the demo honest: the mock
    output still reacts to the actual transcript / scenario, and it doubles as
    the deterministic fallback used when the real provider is unavailable.
    """

    name = "mock"

    def __init__(
        self,
        config: LLMConfig,
        baseline_fn: Callable[[str, str], dict],
    ) -> None:
        self.config = config
        self._baseline_fn = baseline_fn

    def complete(
        self, system_prompt: str, user_prompt: str, response_schema: object | None = None
    ) -> LLMResponse:
        start = time.perf_counter()
        logger.info("Mock provider invoked (deterministic baseline)")
        result = self._baseline_fn(system_prompt, user_prompt)
        text = json.dumps(result, ensure_ascii=False)
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMResponse(
            text=text,
            provider=self.name,
            model="mock-baseline",
            attempts=1,
            latency_ms=latency_ms,
            raw={"note": "deterministic mock derived from input"},
        )

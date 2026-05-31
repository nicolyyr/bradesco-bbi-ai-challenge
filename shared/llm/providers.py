"""LLM provider abstraction.

This module isolates *how* we talk to a model from *what* we ask it. Business
logic depends only on the :class:`LLMProvider` interface and never imports the
OpenAI SDK directly. Two concrete providers are shipped:

* :class:`OpenAIProvider` - the real integration (requires ``OPENAI_API_KEY``).
* :class:`MockProvider`   - a deterministic, offline provider used for tests
  and credential-free demos. It delegates to a caller-supplied function so the
  mock answer is computed from the *actual* input rather than hardcoded.

Both return a :class:`LLMResponse` with the raw text plus metadata useful for
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
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a completion for the given system + user prompts."""


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

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
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

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
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

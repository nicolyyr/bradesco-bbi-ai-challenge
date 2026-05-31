"""Shared, case-agnostic LLM layer.

Public surface used by the business logic of both cases.
"""

from .client import (
    GenerationResult,
    LLMClient,
    SOURCE_FALLBACK,
    SOURCE_LLM,
    SOURCE_MOCK,
)
from .config import (
    PROVIDER_GEMINI,
    PROVIDER_MOCK,
    PROVIDER_OPENAI,
    LLMConfig,
    load_config,
)
from .providers import (
    GeminiProvider,
    LLMError,
    LLMProvider,
    LLMResponse,
    MockProvider,
    OpenAIProvider,
)

__all__ = [
    "GenerationResult",
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "LLMProvider",
    "LLMResponse",
    "GeminiProvider",
    "MockProvider",
    "OpenAIProvider",
    "load_config",
    "PROVIDER_GEMINI",
    "PROVIDER_OPENAI",
    "PROVIDER_MOCK",
    "SOURCE_LLM",
    "SOURCE_MOCK",
    "SOURCE_FALLBACK",
]

"""Shared, case-agnostic LLM layer.

Public surface used by the business logic of both cases.
"""

from .client import (
    GenerationResult,
    LLMClient,
    SOURCE_LLM,
)
from .config import (
    PROVIDER_GEMINI,
    PROVIDER_OPENAI,
    LLMConfig,
    MissingAPIKeyError,
    load_config,
)
from .providers import (
    GeminiProvider,
    LLMError,
    LLMProvider,
    LLMResponse,
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
    "OpenAIProvider",
    "MissingAPIKeyError",
    "load_config",
    "PROVIDER_GEMINI",
    "PROVIDER_OPENAI",
    "SOURCE_LLM",
]

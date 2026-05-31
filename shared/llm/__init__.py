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
from .config import LLMConfig, load_config
from .providers import LLMError, LLMProvider, LLMResponse, MockProvider, OpenAIProvider

__all__ = [
    "GenerationResult",
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "OpenAIProvider",
    "load_config",
    "SOURCE_LLM",
    "SOURCE_MOCK",
    "SOURCE_FALLBACK",
]

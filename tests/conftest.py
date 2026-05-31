"""Shared pytest fixtures and path setup.

Adds the repo root and both case ``src`` dirs to sys.path so tests can import
the modules regardless of where pytest is invoked from. Because the two cases
use flat module names (schema, baseline, ...), tests import them under explicit
package paths (e.g. ``case_1_earnings_tracker.src.schema``) to avoid collisions.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (REPO_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture
def sample_transcript() -> str:
    return (
        "CEO: We delivered a very strong managerial result with record profitability "
        "and ROE above 20%. We are comfortable with the guidance and reaffirm it. "
        "Credit quality and delinquency remain well behaved, reflecting resilience. "
        "However, the macro backdrop is worse than at the start of the year, with "
        "volatility and headwinds we must monitor.\n\n"
        "ANALYST 1: How sustainable is the ROE?\n\n"
        "ANSWERS:\n\nANSWER 1: We avoid giving ROE guidance, but we expect "
        "profitability above 20% recurrently, supported by efficiency, client margin, "
        "and credit mix. We reaffirm the guidance and remain comfortable with it."
    )


@pytest.fixture
def sample_questions() -> str:
    return (
        "Question 1:\nHow sustainable is the ROE and which levers remain available?\n"
    )


@pytest.fixture
def sample_scenario() -> str:
    return (
        "The Central Bank unexpectedly raised interest rates by 2 percentage points. "
        "Inflation remains persistent and economic growth expectations were revised "
        "downward. Credit conditions are tightening and consumer spending is slowing."
    )


@pytest.fixture
def clean_env(monkeypatch):
    """Strip LLM-related env vars so config defaults are deterministic."""
    for var in (
        "LLM_PROVIDER",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_BASE_URL",
        "LLM_TEMPERATURE",
        "LLM_MAX_TOKENS",
        "LLM_MAX_RETRIES",
        "LLM_ALLOW_FALLBACK",
    ):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch

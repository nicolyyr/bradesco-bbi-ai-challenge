"""Case 1 core: turn an earnings-call transcript into a validated analysis.

This module is the seam between business logic and the model. It renders the
versioned prompts, asks the shared :class:`LLMClient` for a structured answer
validated against :class:`EarningsAnalysis`, and supplies the deterministic
baseline as both the mock generator and the fallback payload.

The keyword engine lives in ``baseline.py`` and is used ONLY as mock/fallback -
the primary path is genuine generative AI.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Allow both "import as package" and "run the script directly" execution styles.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from shared.llm import GenerationResult, LLMClient, load_config  # noqa: E402
from shared.llm.logging_utils import get_logger  # noqa: E402

try:  # package-style import
    from .baseline import build_baseline
    from .parser import render_user_prompt
    from .schema import EarningsAnalysis
except ImportError:  # script-style import (python src/main.py)
    from baseline import build_baseline  # type: ignore
    from parser import render_user_prompt  # type: ignore
    from schema import EarningsAnalysis  # type: ignore

logger = get_logger(__name__)


def analyze_earnings_call(
    *,
    transcript: str,
    system_prompt: str,
    user_prompt_template: str,
    company: str = "ITUB4",
    analyst_questions_text: str = "",
    prior_transcript: Optional[str] = None,
    client: Optional[LLMClient] = None,
) -> tuple[EarningsAnalysis, GenerationResult]:
    """Run the full analysis and return (validated_analysis, provenance).

    The deterministic baseline is computed once and reused as (a) the mock
    provider's output and (b) the fallback payload, so the pipeline always
    yields a schema-valid result even with no API key or on an LLM error.
    """
    baseline_payload = build_baseline(
        transcript=transcript,
        company=company,
        analyst_questions_text=analyst_questions_text,
        prior_transcript=prior_transcript,
    )

    def baseline_fn(_system: str, _user: str) -> dict:
        # Mock provider derives its answer from the real input via the baseline.
        return baseline_payload

    if client is None:
        config = load_config()
        client = LLMClient(config=config, baseline_fn=baseline_fn)

    rendered_user = render_user_prompt(
        user_prompt_template,
        company=company,
        transcript=transcript,
        analyst_questions=analyst_questions_text,
        prior_transcript=prior_transcript,
    )

    result = client.generate_structured(
        system_prompt=system_prompt,
        user_prompt=rendered_user,
        schema=EarningsAnalysis,
        fallback_payload=baseline_payload,
    )
    logger.info("Case 1 analysis produced via %s", result.source)
    return result.data, result  # type: ignore[return-value]

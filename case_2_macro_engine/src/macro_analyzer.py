"""Case 2 core: turn a natural-language macro scenario into a validated view.

Mirrors Case 1's design: render versioned prompts, ask the shared LLMClient for
a structured answer validated against :class:`MacroAnalysis`. The model performs
the scenario -> sector/ticker reasoning; there is no rule-based fallback.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from shared.llm import GenerationResult, LLMClient, load_config  # noqa: E402
from shared.llm.logging_utils import get_logger  # noqa: E402

try:
    from .schema import MacroAnalysis
except ImportError:  # script-style import
    from schema import MacroAnalysis  # type: ignore

logger = get_logger(__name__)


def analyze_macro_scenario(
    scenario_text: str,
    *,
    system_prompt: str,
    user_prompt_template: str,
    client: Optional[LLMClient] = None,
) -> tuple[MacroAnalysis, GenerationResult]:
    """Run the macro analysis with generative AI and return (analysis, provenance)."""
    if not scenario_text or not scenario_text.strip():
        raise ValueError("Scenario text is empty; nothing to analyze.")

    if client is None:
        client = LLMClient(config=load_config())

    rendered_user = user_prompt_template.format(scenario=scenario_text)

    result = client.generate_structured(
        system_prompt=system_prompt,
        user_prompt=rendered_user,
        schema=MacroAnalysis,
    )
    logger.info("Case 2 analysis produced via %s", result.source)
    return result.data, result  # type: ignore[return-value]

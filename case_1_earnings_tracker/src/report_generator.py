"""Markdown report generator for Case 1.

Renders the validated :class:`EarningsAnalysis` into an executive report meant
to be read in ~2 minutes. The use case caps this at 400 words, so the report is
trimmed defensively (evidence/takeaway lists are bounded) and a word count is
asserted by the caller/tests.
"""

from __future__ import annotations

from typing import Optional

try:
    from .schema import EarningsAnalysis
except ImportError:  # script-style import
    from schema import EarningsAnalysis  # type: ignore


def _clip(text: str, max_words: int) -> str:
    """Clip a string to ``max_words`` words (executive report stays terse;
    the full text always remains available in the JSON output)."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",.;:") + "…"


WORD_LIMIT = 400


def generate_report(
    analysis: "EarningsAnalysis | dict",
    source_banner: Optional[str] = None,
) -> str:
    if isinstance(analysis, dict):
        analysis = EarningsAnalysis.model_validate(analysis)

    # The LLM can be more verbose than the deterministic baseline. We build the
    # report at decreasing per-item word budgets (scale) until it fits the
    # 400-word executive limit. Full, untruncated content stays in analysis.json.
    for scale in (1.0, 0.85, 0.7, 0.55, 0.4):
        report = _render(analysis, source_banner, scale)
        if len(report.split()) <= WORD_LIMIT:
            return report
    return report  # smallest scale; still returned even if marginally over


def _render(analysis: "EarningsAnalysis", source_banner: Optional[str], scale: float) -> str:
    def c(words: int) -> int:
        return max(4, int(round(words * scale)))

    tone = analysis.management_tone.classification
    confidence = analysis.management_tone.confidence

    # Bound list lengths AND per-item length to respect the 400-word limit.
    evidence = analysis.management_tone.evidence[:3]
    takeaways = analysis.key_takeaways[:5]
    guidance = analysis.guidance[:3]
    changes = analysis.guidance_changes[:3]
    questions = analysis.analyst_questions[:3]
    red_flags = analysis.red_flags[:3]

    ev_md = "\n".join(f"> {_clip(e, c(20))}" for e in evidence) or "> (no verbatim evidence)"
    tk_md = "\n".join(f"- {_clip(t, c(14))}" for t in takeaways) or "- (none)"
    gd_md = "\n".join(f"- {_clip(g, c(18))}" for g in guidance) or "- (none)"
    ch_md = "\n".join(f"- {_clip(c_.change, c(16))}" for c_ in changes) or "- (none)"
    rf_md = "\n".join(
        f"- \"{_clip(r.quote, c(16))}\" — {_clip(r.reason, c(7))}" for r in red_flags
    ) or "- None detected."
    q_md = "\n".join(
        f"- **Q{i}** ({q.response_quality}): {_clip(q.question, c(16))}"
        for i, q in enumerate(questions, start=1)
    ) or "- (none)"

    header = f"_Source: {source_banner}_\n\n" if source_banner else ""

    return f"""# Earnings Call Intelligence Report — {analysis.company}

{header}## Management Tone
**{tone}** (confidence {confidence:.2f})

{ev_md}

## Key Takeaways
{tk_md}

## Guidance
{gd_md}

## Guidance Changes (vs. prior quarter)
{ch_md}

## Top Analyst Questions
{q_md}

## Red Flags
{rf_md}

## Surprise Score
**{analysis.surprise_score.score}/10** — {_clip(analysis.surprise_score.justification, c(35))}
"""

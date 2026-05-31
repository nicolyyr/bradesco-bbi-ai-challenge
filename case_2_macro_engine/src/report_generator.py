"""Markdown report generator for Case 2 (<= 500 words, ~3-minute read)."""

from __future__ import annotations

from typing import Optional

try:
    from .schema import MacroAnalysis
except ImportError:  # script-style import
    from schema import MacroAnalysis  # type: ignore


def _clip(text: str, max_words: int) -> str:
    """Clip a string to ``max_words`` words so the report respects the 500-word
    limit even with a verbose model; full text is preserved in analysis.json."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",.;:") + "…"


def generate_report(
    analysis: "MacroAnalysis | dict",
    source_banner: Optional[str] = None,
) -> str:
    if isinstance(analysis, dict):
        analysis = MacroAnalysis.model_validate(analysis)

    pos_sectors = "\n".join(
        f"- **{s.sector}**: {_clip(s.rationale, 26)}" for s in analysis.positive_sectors[:5]
    ) or "- (none)"
    neg_sectors = "\n".join(
        f"- **{s.sector}**: {_clip(s.rationale, 26)}" for s in analysis.negative_sectors[:5]
    ) or "- (none)"
    pos_tickers = "\n".join(
        f"- **{t.ticker}**: {_clip(t.rationale, 22)}" for t in analysis.positive_tickers[:3]
    ) or "- (none)"
    neg_tickers = "\n".join(
        f"- **{t.ticker}**: {_clip(t.rationale, 22)}" for t in analysis.negative_tickers[:3]
    ) or "- (none)"
    risks = "\n".join(f"- {_clip(r, 26)}" for r in analysis.market_risks[:3]) or "- (none)"

    header = f"_Source: {source_banner}_\n\n" if source_banner else ""

    return f"""# Macro Scenario Analysis — B3

{header}## Scenario
{_clip(analysis.scenario_summary, 40)}

## Top Benefited Sectors
{pos_sectors}

## Top Negatively Impacted Sectors
{neg_sectors}

## Positively Exposed Tickers
{pos_tickers}

## Negatively Exposed Tickers
{neg_tickers}

## Top 3 Risks to the Thesis
{risks}

## Confidence & View
**Confidence: {analysis.confidence_score}/10** — {_clip(analysis.confidence_rationale, 40)}

{_clip(analysis.investment_view, 40)}
"""

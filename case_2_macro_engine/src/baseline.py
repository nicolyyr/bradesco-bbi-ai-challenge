"""Deterministic baseline for Case 2.

Like Case 1's baseline, this is the rule-based engine used ONLY as mock output
and as the LLM fallback - never presented as generative AI. It reuses the
hand-curated B3 sector/ticker knowledge base from ``sector_mapper`` but, unlike
the original implementation, derives confidence_score, scenario_summary and
investment_view from the ACTUAL scenario text instead of hardcoding them.
"""

from __future__ import annotations

from typing import List

try:
    from .sector_mapper import SECTOR_TICKERS, map_sectors
except ImportError:  # script-style import
    from sector_mapper import SECTOR_TICKERS, map_sectors  # type: ignore


# Scenario signals -> derived attributes. Used to make summary/confidence/view
# react to the input rather than being constant.
_SIGNALS = {
    "interest rates": "higher interest rates",
    "rate cut": "lower interest rates",
    "inflation": "persistent inflation",
    "economic growth": "weaker growth expectations",
    "growth expectations": "weaker growth expectations",
    "consumer spending": "slowing consumer spending",
    "credit": "tighter credit conditions",
    "unemployment": "labor-market stress",
    "currency": "currency moves",
    "commodity": "commodity-price swings",
}


def _detected_signals(scenario_lower: str) -> List[str]:
    found: List[str] = []
    for key, label in _SIGNALS.items():
        if key in scenario_lower and label not in found:
            found.append(label)
    return found


def _summarize(scenario_text: str, signals: List[str]) -> str:
    if signals:
        return "Scenario characterized by " + ", ".join(signals) + "."
    # fall back to the first sentence of the actual scenario, not a constant
    first = scenario_text.strip().split(".")[0].strip()
    return (first + ".") if first else "Macro scenario provided without recognized signals."


def _confidence(signals: List[str], pos: list, neg: list) -> tuple[int, str]:
    """Confidence grows with how many signals we recognized and mapped."""
    coverage = len(signals)
    breadth = len(pos) + len(neg)
    score = 3 + min(coverage, 4) + (1 if breadth >= 6 else 0)
    score = max(1, min(10, score))
    rationale = (
        f"Derived from {coverage} recognized macro signal(s) and "
        f"{breadth} mapped sector impacts; deterministic baseline estimate."
    )
    return score, rationale


def _investment_view(pos_sectors: list, neg_sectors: list) -> str:
    if not pos_sectors and not neg_sectors:
        return "Insufficient signal to form a directional view from the baseline."
    top_pos = pos_sectors[0]["sector"] if pos_sectors else "defensives"
    top_neg = neg_sectors[0]["sector"] if neg_sectors else "rate-sensitive names"
    return (
        f"Net defensive tilt: overweight {top_pos.lower()}-type exposure, "
        f"underweight {top_neg.lower()}-type exposure."
    )


def build_baseline(scenario_text: str) -> dict:
    """Return a schema-compatible MacroAnalysis dict, derived from input."""
    scenario_lower = scenario_text.lower()
    signals = _detected_signals(scenario_lower)
    mapping = map_sectors(scenario_text)

    pos_sectors = mapping["positive_sectors"]
    neg_sectors = mapping["negative_sectors"]
    score, conf_rationale = _confidence(signals, pos_sectors, neg_sectors)

    risks = _derive_risks(signals)

    return {
        "scenario_summary": _summarize(scenario_text, signals),
        "positive_sectors": pos_sectors,
        "negative_sectors": neg_sectors,
        "positive_tickers": mapping["positive_tickers"],
        "negative_tickers": mapping["negative_tickers"],
        "market_risks": risks,
        "confidence_score": score,
        "confidence_rationale": conf_rationale,
        "investment_view": _investment_view(pos_sectors, neg_sectors),
    }


def _derive_risks(signals: List[str]) -> List[str]:
    risks: List[str] = []
    labels = set(signals)
    if "higher interest rates" in labels:
        risks.append("Central bank pivots to easing sooner than expected, reversing the rate thesis.")
    if "persistent inflation" in labels:
        risks.append("Inflation surprises to the downside, reducing pressure on consumer names.")
    if "weaker growth expectations" in labels:
        risks.append("Growth proves more resilient than feared, lifting cyclical sectors.")
    # always-present generic tail risks
    risks.append("Global risk sentiment or commodity-price shifts dominate domestic transmission.")
    if len(risks) < 3:
        risks.append("Scenario assumptions only partially materialize, weakening sector dispersion.")
    return risks[:3]

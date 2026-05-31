"""Output contract for Case 2 (macro scenario engine)."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class SectorImpact(BaseModel):
    sector: str
    rationale: str


class TickerImpact(BaseModel):
    ticker: str
    rationale: str


class MacroAnalysis(BaseModel):
    # min_length encodes the PDF's required counts as a hard floor, so an answer
    # missing sectors/tickers/risks is rejected and regenerated rather than
    # shipped. No max: the report slices to the top N, and a hard ceiling would
    # needlessly fail an otherwise-good (generous) answer.
    scenario_summary: str
    positive_sectors: List[SectorImpact] = Field(min_length=5)
    negative_sectors: List[SectorImpact] = Field(min_length=5)
    positive_tickers: List[TickerImpact] = Field(min_length=3)
    negative_tickers: List[TickerImpact] = Field(min_length=3)
    market_risks: List[str] = Field(min_length=3)
    confidence_score: int = Field(ge=1, le=10)
    confidence_rationale: str = ""
    investment_view: str = ""

    def to_dict(self) -> dict:
        return self.model_dump()

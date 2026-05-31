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
    scenario_summary: str
    positive_sectors: List[SectorImpact] = Field(default_factory=list)
    negative_sectors: List[SectorImpact] = Field(default_factory=list)
    positive_tickers: List[TickerImpact] = Field(default_factory=list)
    negative_tickers: List[TickerImpact] = Field(default_factory=list)
    market_risks: List[str] = Field(default_factory=list)
    confidence_score: int = Field(ge=1, le=10)
    confidence_rationale: str = ""
    investment_view: str = ""

    def to_dict(self) -> dict:
        return self.model_dump()

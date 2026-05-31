"""Output contract for Case 1 (earnings-call analysis).

These pydantic models ARE the contract between the LLM and the rest of the
pipeline. The model is instructed to emit exactly this JSON; the client
validates the response against these models before any business code sees it.
Validation is what lets us trust the model's output - and, on a contract
mismatch, regenerate instead of shipping malformed data.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class ManagementTone(BaseModel):
    classification: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)

    @field_validator("classification")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return v.strip().lower()


class GuidanceChange(BaseModel):
    change: str
    impact: str


class AnalystQuestion(BaseModel):
    question: str
    response_summary: str
    response_quality: str

    @field_validator("response_quality")
    @classmethod
    def _quality(cls, v: str) -> str:
        normalized = v.strip().capitalize()
        if normalized not in {"High", "Medium", "Low", "N/a"}:
            # be lenient: unknown labels collapse to Medium rather than failing
            return "Medium"
        return "N/A" if normalized == "N/a" else normalized


class RedFlag(BaseModel):
    quote: str
    reason: str


class SurpriseScore(BaseModel):
    score: int = Field(ge=1, le=10)
    justification: str


class EarningsAnalysis(BaseModel):
    """Top-level validated analysis object."""

    company: str
    management_tone: ManagementTone
    key_takeaways: List[str] = Field(default_factory=list)
    guidance: List[str] = Field(default_factory=list)
    guidance_changes: List[GuidanceChange] = Field(default_factory=list)
    analyst_questions: List[AnalystQuestion] = Field(default_factory=list)
    red_flags: List[RedFlag] = Field(default_factory=list)
    surprise_score: SurpriseScore

    def to_dict(self) -> dict:
        return self.model_dump()

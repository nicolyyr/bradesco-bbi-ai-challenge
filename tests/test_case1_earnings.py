"""Tests for Case 1 (Earnings Call Intelligence Tracker)."""

from __future__ import annotations

import json
import os

import pytest

from shared.llm import LLMClient, load_config
from shared.llm.providers import OpenAIProvider

from case_1_earnings_tracker.src import baseline as c1_baseline
from case_1_earnings_tracker.src.analyzer import analyze_earnings_call
from case_1_earnings_tracker.src.parser import render_user_prompt
from case_1_earnings_tracker.src.report_generator import generate_report
from case_1_earnings_tracker.src.schema import EarningsAnalysis

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
C1 = os.path.join(REPO_ROOT, "case_1_earnings_tracker")


def _load(name):
    with open(os.path.join(C1, "prompts", name), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Baseline correctness (the audit's bug fixes)
# --------------------------------------------------------------------------- #
def test_red_flags_are_verbatim_quotes(sample_transcript):
    payload = c1_baseline.build_baseline(sample_transcript, company="ITUB4")
    assert payload["red_flags"], "expected at least one red flag"
    for rf in payload["red_flags"]:
        # the quote must be a substring of the transcript (verbatim), not a label
        assert rf["quote"].rstrip(".") in sample_transcript.replace("\n", " "), (
            f"red flag quote is not verbatim: {rf['quote']!r}"
        )


def test_surprise_score_uses_whole_transcript(sample_transcript):
    payload = c1_baseline.build_baseline(sample_transcript, company="ITUB4")
    # The original bug always returned 3 from an empty first chunk; with real
    # signals (record/worse than/reaffirm) the score must rise above 3.
    assert payload["surprise_score"]["score"] > 3


def test_analyst_questions_parsed_from_input(sample_questions, sample_transcript):
    payload = c1_baseline.build_baseline(
        sample_transcript, analyst_questions_text=sample_questions
    )
    q = payload["analyst_questions"][0]["question"].lower()
    assert "roe" in q  # taken from the provided questions, not hardcoded


def test_analyst_questions_empty_when_none(sample_transcript):
    payload = c1_baseline.build_baseline(sample_transcript, analyst_questions_text="")
    assert payload["analyst_questions"][0]["response_quality"] == "N/A"


def test_guidance_diff_with_prior_quarter(sample_transcript):
    prior = "We reaffirm the guidance. Delinquency is stable. Profitability is solid."
    payload = c1_baseline.build_baseline(sample_transcript, prior_transcript=prior)
    changes = payload["guidance_changes"]
    assert changes
    assert all("change" in c and "impact" in c for c in changes)
    # a real comparison mentions prior/current counts
    assert any("prior=" in c["change"] for c in changes)


def test_guidance_diff_without_prior_is_explicit(sample_transcript):
    payload = c1_baseline.build_baseline(sample_transcript, prior_transcript=None)
    assert "No prior-quarter transcript" in payload["guidance_changes"][0]["change"]


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #
def test_baseline_payload_validates_against_schema(sample_transcript, sample_questions):
    payload = c1_baseline.build_baseline(
        sample_transcript, analyst_questions_text=sample_questions
    )
    model = EarningsAnalysis.model_validate(payload)  # must not raise
    assert model.company == "ITUB4"
    assert 0.0 <= model.management_tone.confidence <= 1.0


# --------------------------------------------------------------------------- #
# Full flow via mock provider
# --------------------------------------------------------------------------- #
def test_full_flow_mock(clean_env, sample_transcript, sample_questions):
    clean_env.setenv("LLM_PROVIDER", "mock")
    system = _load("system_prompt.txt")
    user = _load("user_prompt.txt")
    analysis, result = analyze_earnings_call(
        transcript=sample_transcript,
        system_prompt=system,
        user_prompt_template=user,
        company="ITUB4",
        analyst_questions_text=sample_questions,
    )
    assert isinstance(analysis, EarningsAnalysis)
    assert result.source == "mock"
    report = generate_report(analysis, source_banner=result.banner())
    assert "Earnings Call Intelligence Report" in report


# --------------------------------------------------------------------------- #
# Full flow via stubbed REAL provider (proves the LLM path is wired)
# --------------------------------------------------------------------------- #
class _FakeOpenAI:
    def __init__(self, content):
        class _C:
            def create(self_inner, **kwargs):
                msg = type("M", (), {"content": content})
                choice = type("Ch", (), {"message": msg})
                return type("Comp", (), {"choices": [choice]})

        self.chat = type("Chat", (), {"completions": _C()})()


def test_full_flow_real_provider_stub(clean_env, sample_transcript, sample_questions):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    payload = {
        "company": "ITUB4",
        "management_tone": {"classification": "optimistic", "confidence": 0.9,
                             "evidence": ["record profitability"]},
        "key_takeaways": ["ROE above 20%"],
        "guidance": ["reaffirmed guidance"],
        "guidance_changes": [{"change": "more macro caution", "impact": "watch credit"}],
        "analyst_questions": [{"question": "ROE?", "response_summary": "above 20%",
                                "response_quality": "High"}],
        "red_flags": [{"quote": "worse than at the start of the year",
                        "reason": "acknowledges deterioration"}],
        "surprise_score": {"score": 6, "justification": "record metrics"},
    }
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAI(json.dumps(payload)))
    client = LLMClient(config=cfg, provider=provider)
    analysis, result = analyze_earnings_call(
        transcript=sample_transcript,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        analyst_questions_text=sample_questions,
        client=client,
    )
    assert result.source == "llm"
    assert analysis.management_tone.classification == "optimistic"
    assert analysis.surprise_score.score == 6


def test_real_provider_failure_falls_back(clean_env, sample_transcript, sample_questions):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAI("totally invalid json"))
    client = LLMClient(config=cfg, provider=provider)
    analysis, result = analyze_earnings_call(
        transcript=sample_transcript,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        analyst_questions_text=sample_questions,
        client=client,
    )
    assert result.source == "fallback"
    assert isinstance(analysis, EarningsAnalysis)


# --------------------------------------------------------------------------- #
# Prompt rendering + report constraints
# --------------------------------------------------------------------------- #
def test_prompt_render_includes_inputs(sample_transcript, sample_questions):
    rendered = render_user_prompt(
        _load("user_prompt.txt"),
        company="ITUB4",
        transcript=sample_transcript,
        analyst_questions=sample_questions,
        prior_transcript=None,
    )
    assert "ITUB4" in rendered
    assert "strong managerial result" in rendered
    assert "none provided" in rendered  # prior-quarter block


def test_report_respects_word_limit_on_real_data(clean_env):
    """The committed full transcript must yield a <=400-word report."""
    clean_env.setenv("LLM_PROVIDER", "mock")
    from case_1_earnings_tracker.src.parser import (
        load_analyst_questions,
        load_prior_transcript,
        load_transcript,
    )

    transcript = load_transcript(os.path.join(C1, "data", "itub4_q1_2026.txt"))
    questions = load_analyst_questions(os.path.join(C1, "data", "analyst_questions.txt"))
    prior = load_prior_transcript(os.path.join(C1, "data", "itub4_q4_2025.txt"))
    analysis, result = analyze_earnings_call(
        transcript=transcript,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        analyst_questions_text=questions,
        prior_transcript=prior,
    )
    report = generate_report(analysis, source_banner=result.banner())
    assert len(report.split()) <= 400, f"report too long: {len(report.split())} words"


def test_data_files_exist_and_nonempty():
    for fname in ("itub4_q1_2026.txt", "analyst_questions.txt", "itub4_q4_2025.txt"):
        path = os.path.join(C1, "data", fname)
        assert os.path.exists(path), f"missing data file: {fname}"
        assert os.path.getsize(path) > 0, f"empty data file: {fname}"

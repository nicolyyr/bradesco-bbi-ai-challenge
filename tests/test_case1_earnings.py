"""Tests for Case 1 (Earnings Call Intelligence Tracker) - pure-LLM."""

from __future__ import annotations

import json
import os

from shared.llm import LLMClient, load_config
from shared.llm.providers import GeminiProvider

from case_1_earnings_tracker.src.analyzer import analyze_earnings_call
from case_1_earnings_tracker.src.parser import render_user_prompt
from case_1_earnings_tracker.src.report_generator import generate_report
from case_1_earnings_tracker.src.schema import EarningsAnalysis

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
C1 = os.path.join(REPO_ROOT, "case_1_earnings_tracker")


def _load(name):
    with open(os.path.join(C1, "prompts", name), encoding="utf-8") as fh:
        return fh.read()


# A complete, schema-valid analysis the fake model will "return".
_VALID_PAYLOAD = {
    "company": "ITUB4",
    "management_tone": {
        "classification": "cautiously optimistic",
        "confidence": 0.8,
        "evidence": [
            "we delivered a very strong managerial result",
            "we are comfortable with the guidance",
            "conditions are worse than at the beginning of the year",
        ],
    },
    "key_takeaways": ["ROE remained above 20%", "Credit quality is well behaved"],
    "guidance": ["Management reaffirmed full-year guidance"],
    "guidance_changes": [
        {"change": "More macro caution vs. prior quarter", "impact": "Watch credit costs"}
    ],
    "analyst_questions": [
        {"question": "Is ROE sustainable?", "response_summary": "Above 20% recurrently.",
         "response_quality": "High"},
        {"question": "Delinquency outlook?", "response_summary": "Stable, well-provisioned.",
         "response_quality": "Medium"},
        {"question": "Rede strategy?", "response_summary": "Client-centric integrated payments.",
         "response_quality": "Medium"},
    ],
    "red_flags": [
        {"quote": "conditions are worse than at the beginning of the year",
         "reason": "acknowledges macro deterioration"}
    ],
    "surprise_score": {"score": 6, "justification": "Disclosed data it normally withholds."},
}


class _FakeGeminiClient:
    """Returns a fixed JSON payload (simulates a real generate_content call)."""

    def __init__(self, payload):
        self._text = json.dumps(payload)

        class _Models:
            def generate_content(self_inner, **kwargs):
                return type("Resp", (), {"text": self._text})

        self.models = _Models()


def _client_with(payload, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gm-test")
    cfg = load_config()
    return LLMClient(config=cfg, provider=GeminiProvider(cfg, client=_FakeGeminiClient(payload)))


# --------------------------------------------------------------------------- #
# Schema contract
# --------------------------------------------------------------------------- #
def test_payload_validates_against_schema():
    model = EarningsAnalysis.model_validate(_VALID_PAYLOAD)
    assert model.company == "ITUB4"
    assert 1 <= model.surprise_score.score <= 10
    assert 0.0 <= model.management_tone.confidence <= 1.0


# --------------------------------------------------------------------------- #
# Full flow via stubbed real Gemini provider
# --------------------------------------------------------------------------- #
def test_full_flow_real_provider_stub(clean_env, sample_transcript, sample_questions):
    client = _client_with(_VALID_PAYLOAD, clean_env)
    analysis, result = analyze_earnings_call(
        transcript=sample_transcript,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        company="ITUB4",
        analyst_questions_text=sample_questions,
        client=client,
    )
    assert result.source == "llm"
    assert isinstance(analysis, EarningsAnalysis)
    assert analysis.surprise_score.score == 6
    report = generate_report(analysis, source_banner=result.banner())
    assert "Earnings Call Intelligence Report" in report
    assert "[LLM]" in report


def test_report_respects_word_limit(clean_env):
    client = _client_with(_VALID_PAYLOAD, clean_env)
    analysis, result = analyze_earnings_call(
        transcript="CEO: short transcript.",
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        analyst_questions_text="",
        client=client,
    )
    report = generate_report(analysis, source_banner=result.banner())
    assert len(report.split()) <= 400


def test_report_word_limit_with_verbose_model(clean_env):
    """Even a very verbose model output must be clipped to <=400 words."""
    verbose = json.loads(json.dumps(_VALID_PAYLOAD))
    long = " ".join(["word"] * 200)
    verbose["management_tone"]["evidence"] = [long, long, long]
    verbose["key_takeaways"] = [long] * 5
    verbose["surprise_score"]["justification"] = long
    client = _client_with(verbose, clean_env)
    analysis, result = analyze_earnings_call(
        transcript="CEO: short.",
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        client=client,
    )
    report = generate_report(analysis, source_banner=result.banner())
    assert len(report.split()) <= 400


# --------------------------------------------------------------------------- #
# Prompt rendering + data files
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


def test_prompt_render_with_prior_quarter(sample_transcript):
    rendered = render_user_prompt(
        _load("user_prompt.txt"),
        company="ITUB4",
        transcript=sample_transcript,
        analyst_questions="",
        prior_transcript="Prior quarter: guidance reaffirmed, ROE 24%.",
    )
    assert "PRIOR-QUARTER TRANSCRIPT" in rendered
    assert "ROE 24%" in rendered


def test_data_files_exist_and_nonempty():
    for fname in ("itub4_q1_2026.txt", "analyst_questions.txt", "itub4_q4_2025.txt"):
        path = os.path.join(C1, "data", fname)
        assert os.path.exists(path), f"missing data file: {fname}"
        assert os.path.getsize(path) > 0, f"empty data file: {fname}"

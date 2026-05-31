"""Tests for Case 2 (Macro Scenario Engine) - pure-LLM."""

from __future__ import annotations

import json
import os

import pytest

from shared.llm import LLMClient, load_config
from shared.llm.providers import GeminiProvider

from case_2_macro_engine.src.macro_analyzer import analyze_macro_scenario
from case_2_macro_engine.src.report_generator import generate_report
from case_2_macro_engine.src.schema import MacroAnalysis

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
C2 = os.path.join(REPO_ROOT, "case_2_macro_engine")


def _load(name):
    with open(os.path.join(C2, "prompts", name), encoding="utf-8") as fh:
        return fh.read()


_VALID_PAYLOAD = {
    "scenario_summary": "Aggressive monetary tightening with weaker growth.",
    "positive_sectors": [
        {"sector": "Banks", "rationale": "Higher rates lift net interest income."},
        {"sector": "Insurance", "rationale": "Higher yields on float."},
        {"sector": "Utilities", "rationale": "Defensive cash flows."},
        {"sector": "Oil & Gas", "rationale": "Cash-generative, resilient."},
        {"sector": "Pulp & Paper", "rationale": "FX-benefiting exporters."},
    ],
    "negative_sectors": [
        {"sector": "Construction", "rationale": "Financing costs rise."},
        {"sector": "Retail", "rationale": "Tighter credit hurts demand."},
        {"sector": "Consumer Discretionary", "rationale": "Spending slows."},
        {"sector": "Capital Goods", "rationale": "Investment appetite falls."},
        {"sector": "Real Estate", "rationale": "Rate-sensitive demand."},
    ],
    "positive_tickers": [
        {"ticker": "ITUB4", "rationale": "Rate-sensitive incumbent lender."},
        {"ticker": "BBAS3", "rationale": "Credit-focused bank."},
        {"ticker": "PETR4", "rationale": "Cash-generative producer."},
    ],
    "negative_tickers": [
        {"ticker": "MRVE3", "rationale": "Mortgage-exposed builder."},
        {"ticker": "MGLU3", "rationale": "Discretionary e-commerce."},
        {"ticker": "CYRE3", "rationale": "Real-estate developer."},
    ],
    "market_risks": [
        "Central bank pivots to easing sooner than expected.",
        "Inflation surprises to the downside.",
        "Growth proves more resilient than feared.",
    ],
    "confidence_score": 7,
    "confidence_rationale": "Clear transmission channels for a rate shock.",
    "investment_view": "Overweight financials, underweight rate-sensitive cyclicals.",
}


class _FakeGeminiClient:
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
def test_payload_validates():
    model = MacroAnalysis.model_validate(_VALID_PAYLOAD)
    assert 1 <= model.confidence_score <= 10
    assert len(model.positive_sectors) == 5
    assert len(model.positive_tickers) == 3


def test_b3_ticker_format():
    model = MacroAnalysis.model_validate(_VALID_PAYLOAD)
    for t in model.positive_tickers + model.negative_tickers:
        assert t.ticker[:4].isalpha()
        assert any(ch.isdigit() for ch in t.ticker)


# --------------------------------------------------------------------------- #
# Full flow via stubbed real provider
# --------------------------------------------------------------------------- #
def test_full_flow_real_stub(clean_env, sample_scenario):
    client = _client_with(_VALID_PAYLOAD, clean_env)
    analysis, result = analyze_macro_scenario(
        sample_scenario,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        client=client,
    )
    assert result.source == "llm"
    assert analysis.confidence_score == 7
    assert analysis.positive_sectors[0].sector == "Banks"
    report = generate_report(analysis, source_banner=result.banner())
    assert "Macro Scenario Analysis" in report
    assert "[LLM]" in report
    assert len(report.split()) <= 500


def test_report_word_limit_with_verbose_model(clean_env, sample_scenario):
    verbose = json.loads(json.dumps(_VALID_PAYLOAD))
    long = " ".join(["word"] * 120)
    for s in verbose["positive_sectors"] + verbose["negative_sectors"]:
        s["rationale"] = long
    verbose["confidence_rationale"] = long
    verbose["investment_view"] = long
    client = _client_with(verbose, clean_env)
    analysis, result = analyze_macro_scenario(
        sample_scenario,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        client=client,
    )
    report = generate_report(analysis, source_banner=result.banner())
    assert len(report.split()) <= 500


def test_empty_scenario_raises(clean_env):
    client = _client_with(_VALID_PAYLOAD, clean_env)
    with pytest.raises(ValueError):
        analyze_macro_scenario(
            "   ",
            system_prompt=_load("system_prompt.txt"),
            user_prompt_template=_load("user_prompt.txt"),
            client=client,
        )


def test_scenario_data_file_exists():
    path = os.path.join(C2, "data", "scenario.txt")
    assert os.path.exists(path) and os.path.getsize(path) > 0

"""Tests for Case 2 (Macro Scenario Engine)."""

from __future__ import annotations

import json
import os

import pytest

from shared.llm import LLMClient, load_config
from shared.llm.providers import OpenAIProvider

from case_2_macro_engine.src import baseline as c2_baseline
from case_2_macro_engine.src.macro_analyzer import analyze_macro_scenario
from case_2_macro_engine.src.report_generator import generate_report
from case_2_macro_engine.src.schema import MacroAnalysis
from case_2_macro_engine.src.sector_mapper import map_sectors

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
C2 = os.path.join(REPO_ROOT, "case_2_macro_engine")


def _load(name):
    with open(os.path.join(C2, "prompts", name), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Baseline derives from input (audit fix: no more hardcoded constants)
# --------------------------------------------------------------------------- #
def test_summary_reflects_input(sample_scenario):
    payload = c2_baseline.build_baseline(sample_scenario)
    # must mention recognized signals, not be a constant string
    assert "interest rates" in payload["scenario_summary"].lower()


def test_summary_differs_across_scenarios():
    hike = c2_baseline.build_baseline("The Central Bank raised interest rates sharply.")
    cut = c2_baseline.build_baseline("The Central Bank announced a large rate cut and easing.")
    assert hike["scenario_summary"] != cut["scenario_summary"]


def test_confidence_is_derived_not_constant():
    rich = c2_baseline.build_baseline(
        "Interest rates up, inflation persistent, growth expectations down, "
        "consumer spending slowing, credit tightening."
    )
    poor = c2_baseline.build_baseline("Something vague happened in the economy.")
    assert rich["confidence_score"] != poor["confidence_score"]
    assert 1 <= rich["confidence_score"] <= 10
    assert 1 <= poor["confidence_score"] <= 10


def test_rate_cut_branch_changes_view():
    cut = c2_baseline.build_baseline("The Central Bank announced a rate cut and easing cycle.")
    sectors = [s["sector"] for s in cut["positive_sectors"]]
    assert "Construction" in sectors or "Retail" in sectors


def test_unrecognized_scenario_still_returns_sectors():
    """Audit fix: previously an unknown scenario produced empty sector lists."""
    payload = c2_baseline.build_baseline("Geopolitical tensions rose in a distant region.")
    assert payload["positive_sectors"], "expected a non-empty defensive fallback"
    assert payload["negative_sectors"]


# --------------------------------------------------------------------------- #
# Sector mapper structure
# --------------------------------------------------------------------------- #
def test_map_sectors_counts(sample_scenario):
    mapping = map_sectors(sample_scenario)
    assert len(mapping["positive_sectors"]) <= 5
    assert len(mapping["negative_sectors"]) <= 5
    assert len(mapping["positive_tickers"]) <= 3
    assert len(mapping["negative_tickers"]) <= 3


def test_tickers_are_b3_format(sample_scenario):
    mapping = map_sectors(sample_scenario)
    for t in mapping["positive_tickers"] + mapping["negative_tickers"]:
        assert t["ticker"][:4].isalpha()
        assert any(ch.isdigit() for ch in t["ticker"])  # B3 tickers end in a number


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #
def test_baseline_validates(sample_scenario):
    payload = c2_baseline.build_baseline(sample_scenario)
    model = MacroAnalysis.model_validate(payload)
    assert 1 <= model.confidence_score <= 10


# --------------------------------------------------------------------------- #
# Full flow (mock + real stub + fallback)
# --------------------------------------------------------------------------- #
def test_full_flow_mock(clean_env, sample_scenario):
    clean_env.setenv("LLM_PROVIDER", "mock")
    analysis, result = analyze_macro_scenario(
        sample_scenario,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
    )
    assert isinstance(analysis, MacroAnalysis)
    assert result.source == "mock"
    report = generate_report(analysis, source_banner=result.banner())
    assert "Macro Scenario Analysis" in report
    assert len(report.split()) <= 500


class _FakeOpenAI:
    def __init__(self, content):
        class _C:
            def create(self_inner, **kwargs):
                msg = type("M", (), {"content": content})
                choice = type("Ch", (), {"message": msg})
                return type("Comp", (), {"choices": [choice]})

        self.chat = type("Chat", (), {"completions": _C()})()


def test_full_flow_real_stub(clean_env, sample_scenario):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    payload = {
        "scenario_summary": "Aggressive monetary tightening with weaker growth.",
        "positive_sectors": [{"sector": "Banks", "rationale": "NII expands with rates."}],
        "negative_sectors": [{"sector": "Construction", "rationale": "Financing costs rise."}],
        "positive_tickers": [{"ticker": "ITUB4", "rationale": "Rate-sensitive lender."}],
        "negative_tickers": [{"ticker": "MRVE3", "rationale": "Mortgage-exposed builder."}],
        "market_risks": ["Sooner-than-expected easing", "Inflation undershoot", "Global shock"],
        "confidence_score": 7,
        "confidence_rationale": "Clear transmission channels.",
        "investment_view": "Overweight financials, underweight builders.",
    }
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAI(json.dumps(payload)))
    client = LLMClient(config=cfg, provider=provider)
    analysis, result = analyze_macro_scenario(
        sample_scenario,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        client=client,
    )
    assert result.source == "llm"
    assert analysis.confidence_score == 7
    assert analysis.positive_sectors[0].sector == "Banks"


def test_real_failure_falls_back(clean_env, sample_scenario):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAI("not json"))
    client = LLMClient(config=cfg, provider=provider)
    analysis, result = analyze_macro_scenario(
        sample_scenario,
        system_prompt=_load("system_prompt.txt"),
        user_prompt_template=_load("user_prompt.txt"),
        client=client,
    )
    assert result.source == "fallback"
    assert isinstance(analysis, MacroAnalysis)


def test_empty_scenario_raises(clean_env):
    clean_env.setenv("LLM_PROVIDER", "mock")
    with pytest.raises(ValueError):
        analyze_macro_scenario(
            "   ",
            system_prompt=_load("system_prompt.txt"),
            user_prompt_template=_load("user_prompt.txt"),
        )


def test_scenario_data_file_exists():
    path = os.path.join(C2, "data", "scenario.txt")
    assert os.path.exists(path) and os.path.getsize(path) > 0

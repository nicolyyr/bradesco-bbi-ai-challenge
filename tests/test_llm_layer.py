"""Tests for the shared, case-agnostic LLM layer (pure-LLM: no mock provider)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from shared.llm import (
    GeminiProvider,
    LLMClient,
    LLMError,
    LLMResponse,
    MissingAPIKeyError,
    OpenAIProvider,
    SOURCE_LLM,
)
from shared.llm.client import _extract_json, _sanitize_json_text
from shared.llm.config import (
    PROVIDER_GEMINI,
    PROVIDER_OPENAI,
    load_config,
    resolve_provider,
)
from shared.llm.providers import _backoff_seconds


class _Toy(BaseModel):
    name: str
    score: int


# --------------------------------------------------------------------------- #
# Fake SDK clients - exercise the REAL providers with no network and no key.
# --------------------------------------------------------------------------- #
class _FakeOpenAIClient:
    """Mimics the subset of the OpenAI SDK we use."""

    def __init__(self, content='{"name": "real", "score": 9}', fail_times=0):
        self._content = content
        self._fail_times = fail_times
        self.calls = 0

        class _Completions:
            def __init__(self, outer):
                self._outer = outer

            def create(self, **kwargs):
                self._outer.calls += 1
                if self._outer.calls <= self._outer._fail_times:
                    raise RuntimeError("simulated transient API error")
                msg = type("M", (), {"content": self._outer._content})
                choice = type("Ch", (), {"message": msg})
                return type("Comp", (), {"choices": [choice]})

        self.chat = type("Chat", (), {"completions": _Completions(self)})()


class _FakeGeminiClient:
    """Mimics client.models.generate_content(...).text from google-genai."""

    def __init__(self, content='{"name": "real", "score": 9}', fail_times=0):
        self._content = content
        self._fail_times = fail_times
        self.calls = 0

        class _Models:
            def __init__(self, outer):
                self._outer = outer

            def generate_content(self, **kwargs):
                self._outer.calls += 1
                if self._outer.calls <= self._outer._fail_times:
                    raise RuntimeError("simulated transient API error")
                return type("Resp", (), {"text": self._outer._content})

        self.models = _Models(self)


# --------------------------------------------------------------------------- #
# Configuration & provider precedence
# --------------------------------------------------------------------------- #
def test_no_key_raises_missing_api_key(clean_env):
    with pytest.raises(MissingAPIKeyError):
        load_config()


def test_provider_resolves_to_gemini_with_key(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    cfg = load_config()
    assert cfg.provider == PROVIDER_GEMINI
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.api_key == "gm-test"


def test_google_api_key_also_selects_gemini(clean_env):
    clean_env.setenv("GOOGLE_API_KEY", "gm-test")
    assert load_config().provider == PROVIDER_GEMINI


def test_provider_resolves_to_openai_with_key(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    assert cfg.provider == PROVIDER_OPENAI
    assert cfg.model == "gpt-4o-mini"


def test_gemini_wins_when_both_keys_present(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    assert cfg.provider == PROVIDER_GEMINI
    assert cfg.api_key == "gm-test"


def test_explicit_openai_overrides_gemini_key(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    clean_env.setenv("LLM_PROVIDER", "openai")
    cfg = load_config()
    assert cfg.provider == PROVIDER_OPENAI
    assert cfg.api_key == "sk-test"


def test_custom_model_via_env(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    assert load_config().model == "gemini-2.5-pro"


def test_resolve_provider_rejects_unknown():
    with pytest.raises(ValueError):
        resolve_provider("anthropic", gemini_key="g", openai_key=None)


def test_resolve_provider_precedence_and_missing_key():
    assert resolve_provider(None, "g", "o") == PROVIDER_GEMINI
    assert resolve_provider(None, None, "o") == PROVIDER_OPENAI
    with pytest.raises(MissingAPIKeyError):
        resolve_provider(None, None, None)


# --------------------------------------------------------------------------- #
# JSON extraction & sanitization
# --------------------------------------------------------------------------- #
def test_extract_plain_json():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_embedded_in_prose():
    assert _extract_json('Sure! Here it is: {"a": 1} Hope that helps.') == {"a": 1}


def test_extract_json_strips_bad_control_chars():
    # a raw bell char (0x07) inside a string value breaks json.loads; the
    # sanitizer removes it so the object still parses.
    assert _extract_json('{"a": "x\x07y"}')["a"] == "xy"


def test_extract_json_empty_raises():
    with pytest.raises(ValueError):
        _extract_json("")


def test_sanitize_strips_control_chars():
    assert "\x07" not in _sanitize_json_text('{"a":"x\x07y"}')


# --------------------------------------------------------------------------- #
# Backoff respects server-suggested retry delay
# --------------------------------------------------------------------------- #
def test_backoff_uses_server_retry_delay():
    err = RuntimeError("429 RESOURCE_EXHAUSTED ... Please retry in 24s ...")
    # should be at least the suggested 24s (plus margin), capped at 30
    assert 24.0 <= _backoff_seconds(err, attempt=1) <= 30.0


def test_backoff_exponential_without_hint():
    err = RuntimeError("some transient error")
    assert _backoff_seconds(err, attempt=1) <= 8.0


# --------------------------------------------------------------------------- #
# Gemini real path (stubbed client)
# --------------------------------------------------------------------------- #
def test_gemini_provider_with_injected_client(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    cfg = load_config()
    provider = GeminiProvider(cfg, client=_FakeGeminiClient())
    client = LLMClient(config=cfg, provider=provider)
    result = client.generate_structured(system_prompt="s", user_prompt="u", schema=_Toy)
    assert result.source == SOURCE_LLM
    assert result.provider == "gemini"
    assert result.data.name == "real" and result.data.score == 9


def test_gemini_provider_retries_then_succeeds(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("LLM_MAX_RETRIES", "2")
    cfg = load_config()
    fake = _FakeGeminiClient(fail_times=1)
    resp = GeminiProvider(cfg, client=fake).complete("s", "u")
    assert isinstance(resp, LLMResponse)
    assert fake.calls == 2 and resp.attempts == 2


def test_gemini_provider_raises_after_exhausting_retries(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("LLM_MAX_RETRIES", "1")
    cfg = load_config()
    provider = GeminiProvider(cfg, client=_FakeGeminiClient(fail_times=99))
    with pytest.raises(LLMError):
        provider.complete("s", "u")


def test_gemini_provider_without_key_errors(clean_env):
    clean_env.setenv("LLM_PROVIDER", "gemini")
    clean_env.setenv("GEMINI_API_KEY", "x")  # needed so load_config resolves gemini
    cfg = load_config()
    # now blank the key on the frozen config via a fresh one without the key
    clean_env.delenv("GEMINI_API_KEY", raising=False)
    clean_env.setenv("LLM_PROVIDER", "gemini")
    # build a config object with no api_key by going through resolve path is awkward;
    # instead instantiate provider with a config that has api_key=None.
    from shared.llm.config import LLMConfig
    bare = LLMConfig(provider="gemini", model="gemini-2.5-flash", api_key=None,
                     base_url=None, temperature=0.2, max_tokens=8000,
                     max_retries=1, log_level="INFO")
    with pytest.raises(LLMError):
        GeminiProvider(bare).complete("s", "u")  # no injected client, no key


# --------------------------------------------------------------------------- #
# OpenAI real path (stubbed client)
# --------------------------------------------------------------------------- #
def test_openai_provider_with_injected_client(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAIClient())
    client = LLMClient(config=cfg, provider=provider)
    result = client.generate_structured(system_prompt="s", user_prompt="u", schema=_Toy)
    assert result.source == SOURCE_LLM
    assert result.provider == "openai"
    assert result.data.score == 9


def test_openai_provider_retries_then_succeeds(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    clean_env.setenv("LLM_MAX_RETRIES", "2")
    cfg = load_config()
    fake = _FakeOpenAIClient(fail_times=1)
    resp = OpenAIProvider(cfg, client=fake).complete("s", "u")
    assert fake.calls == 2 and resp.attempts == 2


# --------------------------------------------------------------------------- #
# Regeneration on malformed JSON, then raise (no fallback)
# --------------------------------------------------------------------------- #
def test_client_regenerates_on_invalid_json_then_succeeds(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    cfg = load_config()

    # first call returns garbage, second returns valid JSON
    class _FlakyClient:
        def __init__(self):
            self.calls = 0
            outer = self

            class _Models:
                def generate_content(self, **kwargs):
                    outer.calls += 1
                    text = "not json" if outer.calls == 1 else '{"name":"ok","score":5}'
                    return type("Resp", (), {"text": text})

            self.models = _Models()

    flaky = _FlakyClient()
    client = LLMClient(config=cfg, provider=GeminiProvider(cfg, client=flaky))
    result = client.generate_structured(system_prompt="s", user_prompt="u", schema=_Toy)
    assert result.source == SOURCE_LLM
    assert result.data.score == 5
    assert flaky.calls == 2  # regenerated once


def test_client_raises_when_all_regens_invalid(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("LLM_MAX_RETRIES", "0")  # no per-call retry; each gen = 1 call
    cfg = load_config()
    client = LLMClient(config=cfg, provider=GeminiProvider(cfg, client=_FakeGeminiClient(content="garbage")))
    with pytest.raises((ValueError, LLMError)):
        client.generate_structured(system_prompt="s", user_prompt="u", schema=_Toy)


def test_client_raises_on_schema_violation(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("LLM_MAX_RETRIES", "0")
    cfg = load_config()
    # valid JSON but missing required "score" -> ValidationError on every regen
    client = LLMClient(config=cfg, provider=GeminiProvider(cfg, client=_FakeGeminiClient(content='{"name":"x"}')))
    with pytest.raises(Exception):
        client.generate_structured(system_prompt="s", user_prompt="u", schema=_Toy)

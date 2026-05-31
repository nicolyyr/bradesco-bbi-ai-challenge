"""Tests for the shared, case-agnostic LLM layer."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from shared.llm import (
    GeminiProvider,
    LLMClient,
    LLMError,
    LLMResponse,
    MockProvider,
    OpenAIProvider,
    SOURCE_FALLBACK,
    SOURCE_LLM,
    SOURCE_MOCK,
)
from shared.llm.client import _extract_json
from shared.llm.config import (
    PROVIDER_GEMINI,
    PROVIDER_MOCK,
    PROVIDER_OPENAI,
    load_config,
    resolve_provider,
)


class _Toy(BaseModel):
    name: str
    score: int


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def test_provider_resolves_to_mock_without_key(clean_env):
    cfg = load_config()
    assert cfg.provider == PROVIDER_MOCK
    assert cfg.is_mock is True


def test_provider_resolves_to_gemini_with_key(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test-not-real")
    cfg = load_config()
    assert cfg.provider == PROVIDER_GEMINI
    assert cfg.is_mock is False
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.api_key == "gm-test-not-real"


def test_google_api_key_also_selects_gemini(clean_env):
    clean_env.setenv("GOOGLE_API_KEY", "gm-test-not-real")
    assert load_config().provider == PROVIDER_GEMINI


def test_provider_resolves_to_openai_with_key(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test-not-real")
    cfg = load_config()
    assert cfg.provider == PROVIDER_OPENAI
    assert cfg.is_mock is False
    assert cfg.model == "gpt-4o-mini"


def test_gemini_wins_when_both_keys_present(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    assert cfg.provider == PROVIDER_GEMINI
    assert cfg.api_key == "gm-test"  # the Gemini key, not the OpenAI one


def test_explicit_provider_overrides_keys(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("OPENAI_API_KEY", "sk-test-not-real")
    clean_env.setenv("LLM_PROVIDER", "mock")
    assert load_config().provider == PROVIDER_MOCK


def test_explicit_openai_overrides_gemini_key(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    clean_env.setenv("LLM_PROVIDER", "openai")
    cfg = load_config()
    assert cfg.provider == PROVIDER_OPENAI
    assert cfg.api_key == "sk-test"


def test_custom_models_via_env(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    assert load_config().model == "gemini-2.5-pro"


def test_resolve_provider_rejects_unknown():
    with pytest.raises(ValueError):
        resolve_provider("anthropic", gemini_key=None, openai_key=None)


def test_resolve_provider_precedence():
    assert resolve_provider(None, "g", "o") == PROVIDER_GEMINI
    assert resolve_provider(None, None, "o") == PROVIDER_OPENAI
    assert resolve_provider(None, None, None) == PROVIDER_MOCK
    assert resolve_provider("mock", "g", "o") == PROVIDER_MOCK


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #
def test_extract_plain_json():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_embedded_in_prose():
    assert _extract_json('Sure! Here it is: {"a": 1} Hope that helps.') == {"a": 1}


def test_extract_json_empty_raises():
    with pytest.raises(ValueError):
        _extract_json("")


# --------------------------------------------------------------------------- #
# Mock provider + client happy path
# --------------------------------------------------------------------------- #
def test_mock_provider_derives_from_input(clean_env):
    def baseline(_s, _u):
        return {"name": "ok", "score": 7}

    client = LLMClient(baseline_fn=baseline)
    result = client.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        schema=_Toy,
        fallback_payload={"name": "fb", "score": 0},
    )
    assert result.source == SOURCE_MOCK
    assert result.data.name == "ok"
    assert result.data.score == 7
    assert result.used_fallback is False


# --------------------------------------------------------------------------- #
# Real provider path with a stubbed client (no network, no key needed)
# --------------------------------------------------------------------------- #
class _FakeChoices:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoices(content)]


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
                return _FakeCompletion(self._outer._content)

        self.chat = type("Chat", (), {"completions": _Completions(self)})()


class _FakeGeminiClient:
    """Mimics the subset of the google-genai SDK we use:
    client.models.generate_content(...).text
    """

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


def test_gemini_provider_with_injected_client(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    cfg = load_config()
    provider = GeminiProvider(cfg, client=_FakeGeminiClient())
    client = LLMClient(config=cfg, provider=provider)
    result = client.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        schema=_Toy,
        fallback_payload={"name": "fb", "score": 0},
    )
    assert result.source == SOURCE_LLM
    assert result.provider == "gemini"
    assert result.data.name == "real"
    assert result.data.score == 9


def test_gemini_provider_retries_then_succeeds(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("LLM_MAX_RETRIES", "2")
    cfg = load_config()
    fake = _FakeGeminiClient(fail_times=1)
    provider = GeminiProvider(cfg, client=fake)
    resp = provider.complete("sys", "usr")
    assert isinstance(resp, LLMResponse)
    assert fake.calls == 2
    assert resp.attempts == 2
    assert resp.provider == "gemini"


def test_gemini_provider_raises_after_exhausting_retries(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    clean_env.setenv("LLM_MAX_RETRIES", "1")
    cfg = load_config()
    provider = GeminiProvider(cfg, client=_FakeGeminiClient(fail_times=99))
    with pytest.raises(LLMError):
        provider.complete("sys", "usr")


def test_gemini_provider_without_key_errors(clean_env):
    clean_env.setenv("LLM_PROVIDER", "gemini")
    cfg = load_config()
    provider = GeminiProvider(cfg)  # no client, no key
    with pytest.raises(LLMError):
        provider.complete("sys", "usr")


def test_gemini_fallback_on_invalid_json(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "gm-test")
    cfg = load_config()
    provider = GeminiProvider(cfg, client=_FakeGeminiClient(content="not json"))
    client = LLMClient(config=cfg, provider=provider)
    result = client.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        schema=_Toy,
        fallback_payload={"name": "fb", "score": 4},
    )
    assert result.source == SOURCE_FALLBACK
    assert result.data.name == "fb"


def test_openai_provider_with_injected_client(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAIClient())
    client = LLMClient(config=cfg, provider=provider)
    result = client.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        schema=_Toy,
        fallback_payload={"name": "fb", "score": 0},
    )
    assert result.source == SOURCE_LLM
    assert result.provider == "openai"
    assert result.data.name == "real"
    assert result.data.score == 9


def test_openai_provider_retries_then_succeeds(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    clean_env.setenv("LLM_MAX_RETRIES", "2")
    cfg = load_config()
    fake = _FakeOpenAIClient(fail_times=1)
    provider = OpenAIProvider(cfg, client=fake)
    resp = provider.complete("sys", "usr")
    assert isinstance(resp, LLMResponse)
    assert fake.calls == 2  # failed once, succeeded on second
    assert resp.attempts == 2


def test_openai_provider_raises_after_exhausting_retries(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    clean_env.setenv("LLM_MAX_RETRIES", "1")
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAIClient(fail_times=99))
    with pytest.raises(LLMError):
        provider.complete("sys", "usr")


# --------------------------------------------------------------------------- #
# Fallback behaviour
# --------------------------------------------------------------------------- #
def test_fallback_used_on_invalid_json(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAIClient(content="not json at all"))
    client = LLMClient(config=cfg, provider=provider)
    result = client.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        schema=_Toy,
        fallback_payload={"name": "fb", "score": 3},
    )
    assert result.source == SOURCE_FALLBACK
    assert result.used_fallback is True
    assert result.data.name == "fb"


def test_fallback_used_on_schema_violation(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    cfg = load_config()
    # missing required "score" field -> validation error -> fallback
    provider = OpenAIProvider(cfg, client=_FakeOpenAIClient(content='{"name": "x"}'))
    client = LLMClient(config=cfg, provider=provider)
    result = client.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        schema=_Toy,
        fallback_payload={"name": "fb", "score": 1},
    )
    assert result.source == SOURCE_FALLBACK


def test_no_fallback_raises_when_disabled(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    clean_env.setenv("LLM_ALLOW_FALLBACK", "false")
    cfg = load_config()
    provider = OpenAIProvider(cfg, client=_FakeOpenAIClient(content="garbage"))
    client = LLMClient(config=cfg, provider=provider)
    with pytest.raises((LLMError, ValueError)):
        client.generate_structured(
            system_prompt="sys",
            user_prompt="usr",
            schema=_Toy,
            fallback_payload=None,
        )


# --------------------------------------------------------------------------- #
# Missing configuration
# --------------------------------------------------------------------------- #
def test_openai_provider_without_key_errors(clean_env):
    """Real provider with no key (and no injected client) must error clearly."""
    clean_env.setenv("LLM_PROVIDER", "openai")
    cfg = load_config()
    provider = OpenAIProvider(cfg)  # no client, no key
    with pytest.raises(LLMError):
        provider.complete("sys", "usr")


def test_mock_client_requires_baseline_fn(clean_env):
    with pytest.raises(ValueError):
        LLMClient()  # mock provider but no baseline_fn supplied


def test_mock_provider_unit(clean_env):
    cfg = load_config()
    provider = MockProvider(cfg, baseline_fn=lambda s, u: {"name": "z", "score": 2})
    resp = provider.complete("sys", "usr")
    assert resp.provider == "mock"
    assert '"name"' in resp.text

# Test Results

Reproducible evidence that the solution works. Run it yourself:

```bash
make install      # create .venv and install deps
pytest -v         # or: make test
```

The suite needs **no API key and no network** — both real providers (Gemini and
OpenAI) are exercised through an **injected fake SDK client**, so the genuine
provider code path (request shape, response parsing, schema validation, retries,
regeneration) runs end-to-end without spending a token.

## Latest run (verbatim)

```text
============================= test session starts ==============================
collected 39 items

tests/test_case1_earnings.py::test_payload_validates_against_schema       PASSED
tests/test_case1_earnings.py::test_full_flow_real_provider_stub           PASSED
tests/test_case1_earnings.py::test_report_respects_word_limit             PASSED
tests/test_case1_earnings.py::test_report_word_limit_with_verbose_model   PASSED
tests/test_case1_earnings.py::test_prompt_render_includes_inputs          PASSED
tests/test_case1_earnings.py::test_prompt_render_with_prior_quarter       PASSED
tests/test_case1_earnings.py::test_data_files_exist_and_nonempty          PASSED
tests/test_case2_macro.py::test_payload_validates                         PASSED
tests/test_case2_macro.py::test_b3_ticker_format                          PASSED
tests/test_case2_macro.py::test_full_flow_real_stub                       PASSED
tests/test_case2_macro.py::test_report_word_limit_with_verbose_model      PASSED
tests/test_case2_macro.py::test_empty_scenario_raises                     PASSED
tests/test_case2_macro.py::test_scenario_data_file_exists                 PASSED
tests/test_llm_layer.py::test_no_key_raises_missing_api_key               PASSED
tests/test_llm_layer.py::test_provider_resolves_to_gemini_with_key        PASSED
tests/test_llm_layer.py::test_google_api_key_also_selects_gemini          PASSED
tests/test_llm_layer.py::test_provider_resolves_to_openai_with_key        PASSED
tests/test_llm_layer.py::test_gemini_wins_when_both_keys_present          PASSED
tests/test_llm_layer.py::test_explicit_openai_overrides_gemini_key        PASSED
tests/test_llm_layer.py::test_custom_model_via_env                        PASSED
tests/test_llm_layer.py::test_resolve_provider_rejects_unknown            PASSED
tests/test_llm_layer.py::test_resolve_provider_precedence_and_missing_key PASSED
tests/test_llm_layer.py::test_extract_plain_json                          PASSED
tests/test_llm_layer.py::test_extract_fenced_json                         PASSED
tests/test_llm_layer.py::test_extract_json_embedded_in_prose              PASSED
tests/test_llm_layer.py::test_extract_json_strips_bad_control_chars       PASSED
tests/test_llm_layer.py::test_extract_json_empty_raises                   PASSED
tests/test_llm_layer.py::test_sanitize_strips_control_chars               PASSED
tests/test_llm_layer.py::test_backoff_uses_server_retry_delay             PASSED
tests/test_llm_layer.py::test_backoff_exponential_without_hint            PASSED
tests/test_llm_layer.py::test_gemini_provider_with_injected_client        PASSED
tests/test_llm_layer.py::test_gemini_provider_retries_then_succeeds       PASSED
tests/test_llm_layer.py::test_gemini_provider_raises_after_exhausting_retries PASSED
tests/test_llm_layer.py::test_gemini_provider_without_key_errors          PASSED
tests/test_llm_layer.py::test_openai_provider_with_injected_client        PASSED
tests/test_llm_layer.py::test_openai_provider_retries_then_succeeds       PASSED
tests/test_llm_layer.py::test_client_regenerates_on_invalid_json_then_succeeds PASSED
tests/test_llm_layer.py::test_client_raises_when_all_regens_invalid       PASSED
tests/test_llm_layer.py::test_client_raises_on_schema_violation           PASSED

============================== 39 passed in 6.40s ==============================
```

## What the 39 tests cover

| Area | Tests | What it proves |
|---|---|---|
| **Provider selection & precedence** | 9 | Gemini is the default; an explicit `LLM_PROVIDER` wins; missing key raises `MissingAPIKeyError` (generative AI is mandatory). |
| **Real Gemini path** (injected client) | 5 | `generate_content` is called with the schema; valid output is parsed and validated; retries honor a 429's `retryDelay`; no key raises. |
| **Real OpenAI path** (injected client) | 2 | `chat.completions.create` path parses and validates; retries work. |
| **JSON parsing & sanitization** | 6 | Bare JSON, fenced JSON, JSON-in-prose, and control-char pollution all parse; empty raises. |
| **Resilience (regenerate, then raise)** | 3 | A malformed first answer triggers regeneration and then succeeds; if all attempts fail, the call raises (no silent fallback). |
| **Schema / output contract** | 4 | `EarningsAnalysis` / `MacroAnalysis` enforce field types and bounds (e.g. surprise 1–10, confidence 0–1, Case 2 minimum counts). |
| **End-to-end flows** | 2 | Both cases run prompt → LLM (stubbed) → validated model → report. |
| **Report word limits** | 4 | Case 1 ≤ 400 and Case 2 ≤ 500 words hold even when the model is deliberately verbose. |

## Live (real-API) runs

The committed `outputs/` were produced by **real** Gemini calls — see
[LLM_EXAMPLES.md](LLM_EXAMPLES.md). Each report's first line carries a runtime
banner such as `[LLM] gemini:gemini-2.5-flash (1 attempt(s), 7647 ms)` generated
in `shared/llm/client.py` (not hardcoded), with real, varying latencies.

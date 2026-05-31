# Bradesco BBI AI Challenge — Equity Strategy Tech/AI Cases

Two Python tools that turn unstructured financial text into structured,
decision-grade equity-strategy intelligence using **generative AI** with
explicit, versioned **prompt engineering**:

- **Case 1 — Earnings Call Intelligence Tracker:** an earnings-call transcript →
  structured analysis (tone with verbatim evidence, guidance changes vs. the
  prior quarter, top analyst questions, linguistic red flags, surprise score) +
  a ≤400-word executive report.
- **Case 2 — Macro Scenario Engine:** a macro scenario in natural language →
  top-5 benefited/hurt sectors with transmission mechanism, 3+3 B3 tickers,
  top-3 thesis risks, confidence score + a ≤500-word report.

---

## Table of contents
1. [Problem & use case](#problem--use-case)
2. [What the solution does](#what-the-solution-does)
3. [Architecture](#architecture)
4. [Where generative AI is used](#where-generative-ai-is-used)
5. [Prompt engineering](#prompt-engineering)
6. [Prerequisites](#prerequisites)
7. [Installation](#installation)
8. [Configuration](#configuration)
9. [Running locally](#running-locally)
10. [Tests](#tests)
11. [Troubleshooting](#troubleshooting)
12. [Time log](#time-log)
13. [Prioritization rationale](#prioritization-rationale)
14. [Three most serious limitations](#three-most-serious-limitations)
15. [If I had two more weeks](#if-i-had-two-more-weeks)
16. [Risks](#risks)

---

## Problem & use case

Equity Strategy translates rich-but-unstructured inputs into actionable views.
Two recurring, time-consuming tasks:

- **Earnings calls** (60–90 min) carry guidance, strategy signals and nuanced
  Q&A that consensus takes days to digest. We want the signal in minutes.
- **Macro → sector → ticker** translation is manual: read reports, debate
  transmission channels, land on a sector view. We want a prototype that
  accelerates that translation.

Both tasks are explicitly *Tech/AI*: the challenge evaluates how software
engineering is combined with **generative AI** and **prompt engineering**.

## What the solution does

| | Case 1 | Case 2 |
|---|---|---|
| Input | earnings transcript (+ analyst questions, + optional prior quarter) | macro scenario (free text / file / stdin) |
| Core AI output | tone+evidence, takeaways, guidance, **guidance changes vs. prior quarter**, top-3 analyst Q&A, **verbatim red flags**, **surprise score** | top-5 +/− sectors with transmission mechanism, 3+3 B3 tickers, top-3 risks, confidence |
| Deliverables | `analysis.json` + `report.md` (≤400 words) | `analysis.json` + `report.md` (≤500 words) |

## Architecture

High level (full detail in [ARCHITECTURE.md](ARCHITECTURE.md)):

```mermaid
flowchart TD
    IN[Input text] --> R[Prompt rendering<br/>versioned system + user templates]
    R --> CL[shared/llm: LLMClient]
    CL -->|provider=gemini| GEM[GeminiProvider<br/>real GenAI - default]
    CL -->|provider=openai| OAI[OpenAIProvider<br/>real GenAI - alt]
    GEM --> V[Parse + validate against<br/>pydantic schema]
    OAI --> V
    V -->|valid| OUT[Validated model]
    V -->|invalid| RG[Regenerate<br/>up to 3 attempts]
    RG --> V
    V -->|unrecoverable| ERR[Raise — no silent degradation]
    OUT --> J[analysis.json]
    OUT --> MD[report.md]
```

**Separation of concerns:** business logic (`*/src/analyzer.py`,
`macro_analyzer.py`) depends only on the case-agnostic `shared/llm` layer and
never touches the SDK or parses JSON itself. Generative AI is mandatory: there
is no mock or fallback path — every result is model-authored.

### Components
- `shared/llm/` — provider abstraction, config (env), JSON parsing + schema
  validation, retries, regeneration, structured logging.
- `case_1_earnings_tracker/` — Case 1 prompts, schema, analyzer,
  report generator, entrypoint, data.
- `case_2_macro_engine/` — same structure for Case 2.
- `demo.py`, `Makefile` — one-command runners.
- `tests/` — 39 automated tests (pytest).

## Where generative AI is used

The model performs the **core extraction/reasoning** in both cases:

- **Case 1:** `case_1_earnings_tracker/src/analyzer.py` →
  `shared/llm/client.py::LLMClient.generate_structured` →
  `GeminiProvider.complete` (or `OpenAIProvider.complete`) in
  `shared/llm/providers.py`, using structured output and the versioned prompts
  in `case_1_earnings_tracker/prompts/`.
- **Case 2:** `case_2_macro_engine/src/macro_analyzer.py` → same client → same
  provider, with `case_2_macro_engine/prompts/`.

Provenance is explicit at runtime: every run prints a single
`[LLM] provider:model (N attempt(s), X ms)` banner so you can prove which model
produced the answer. There is no mock or fallback — generative AI is mandatory.

## Prompt engineering

Prompts are **versioned files** (not inline strings), one `system_prompt.txt`
and one `user_prompt.txt` per case, with an explicit JSON output contract and
anti-hallucination rules (grounding, verbatim quotes, "say what you don't
know"). Full rationale, variables, and evolution strategy are documented in
[PROMPT_ENGINEERING.md](PROMPT_ENGINEERING.md).

## Prerequisites
- Python 3.10+ (developed and validated on 3.13).
- `make` (optional; all commands have a plain-Python equivalent).
- A Gemini API key (free tier) **or** an OpenAI key. Generative AI is mandatory;
  without a key `load_config()` raises `MissingAPIKeyError`.

## Installation

```bash
# from the repository root
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or simply:  make install
```

## Configuration

Copy the template and edit as needed:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | auto | `gemini` or `openai`. Empty → auto (gemini key → gemini, else openai key → openai). |
| `GEMINI_API_KEY` | — | Default provider. Free tier at [AI Studio](https://aistudio.google.com/apikey). `GOOGLE_API_KEY` also accepted. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model (native structured output via `response_schema`). |
| `OPENAI_API_KEY` | — | Alternative provider. Leave empty to use Gemini. |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model (JSON mode). |
| `OPENAI_BASE_URL` | — | Optional OpenAI-compatible gateway. |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature. |
| `LLM_MAX_TOKENS` | `8000` | Max completion tokens. |
| `LLM_MAX_RETRIES` | `4` | Retries on transient API errors (honors a 429's server-suggested `retryDelay`). |
| `LLM_LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`. |

**No secrets are committed.** `.env` is git-ignored; only `.env.example` (no
keys) is tracked.

## Running locally

Each case runs from anywhere (paths resolve to the repo root):

```bash
# Case 1
python case_1_earnings_tracker/src/main.py
# custom inputs:
python case_1_earnings_tracker/src/main.py --company ITUB4 \
    --transcript case_1_earnings_tracker/data/itub4_q1_2026.txt \
    --prior case_1_earnings_tracker/data/itub4_q4_2025.txt

# Case 2
python case_2_macro_engine/src/main.py
python case_2_macro_engine/src/main.py --scenario case_2_macro_engine/data/scenario.txt
echo "The Selic was cut 200bps amid an easing cycle." | \
    python case_2_macro_engine/src/main.py --stdin
```

Outputs are written to each case's `outputs/{analysis.json,report.md}`.

## Tests

```bash
pytest -q             # or: make test
make validate         # install + test + demo, end to end
```

39 tests cover: provider selection & precedence (Gemini default), the Gemini and
OpenAI real paths (exercised via an injected fake SDK client — no network, no
key), retries, JSON parsing/sanitization, schema validation, regeneration on
malformed JSON then raising, `MissingAPIKeyError` when no key is present, both
end-to-end flows, the report word limits, and the data files.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `MissingAPIKeyError` at startup | no API key set | export `GEMINI_API_KEY` (free tier) or `OPENAI_API_KEY`. A key is mandatory — there is no offline/mock mode. |
| Run fails after retries with a 429/quota error | provider rate limit or quota exhausted | wait and retry (the client already honors the 429's server-suggested `retryDelay` across `LLM_MAX_RETRIES`), or switch provider with `LLM_PROVIDER`. No fallback by design. |
| `ModuleNotFoundError: google` / `openai` | deps not installed | `pip install -r requirements.txt`. |
| Report slightly over word limit | verbose model | the report generator clips to the limit defensively; you may also lower `LLM_MAX_TOKENS` or tighten the prompt. |
| Repeated invalid/malformed JSON | model not honoring the contract | the client regenerates up to 3 times; persistent failure raises (`LLM_LOG_LEVEL=DEBUG` shows the raw output). |

## Time log
_Approximate, honest._

| Activity | Time |
|---|---|
| Reading the case, setup, data prep | ~1.5 h |
| Shared LLM layer (providers, config, validation, retries + regeneration) | ~3 h |
| Case 1 (prompts, schema, analyzer, report, bug fixes) | ~3 h |
| Case 2 (prompts, schema, analyzer, report) | ~2 h |
| Multi-provider support (Gemini default + OpenAI) | ~1 h |
| Tests (39) | ~2 h |
| Documentation (this README + 3 docs) | ~2 h |
| **Total** | **~14.5 h** |

## Prioritization rationale

I invested in **both cores equally** and then **deepened Case 1** as the
"extension" case. Reasoning: Case 1 is the harder NLP problem (long transcript,
nuance, grounding, temporal comparison), so it best demonstrates prompt
engineering and anti-hallucination discipline. Concretely, Case 1 received the
extra investment via:
- **Citation tracking** (verbatim evidence + verbatim red-flag quotes);
- **Temporal comparison** (real guidance-change diff vs. a prior quarter);
- a **self-correcting output contract** (schema validation + regeneration).

A cross-cutting investment benefiting both: the **resilient LLM layer**
(retries that honor 429 `retryDelay`, regeneration on invalid JSON, and Gemini
native structured output) and a **39-test** safety net, which I judged more
valuable for a defensible, demonstrable delivery than adding more thin
extensions.

## Three most serious limitations
1. **Single-call extraction for long transcripts.** Case 1 sends the transcript
   in one prompt. Very long calls can exceed context or dilute attention; there
   is no chunk-map-reduce or retrieval step yet. *(Mitigation: the report stays
   terse; full data is in JSON. Not yet solved for >context-window transcripts.)*
2. **Live runs depend on API availability/quota.** Generative AI is mandatory
   and there is no offline fallback by design. A 429/quota error that persists
   after `LLM_MAX_RETRIES` (which honor the server-suggested `retryDelay`) fails
   the run. *(Mitigation: Gemini's free tier, plus the ability to switch
   provider via `LLM_PROVIDER`. Not solved without an active key/quota.)*
3. **No grounding verification of model claims.** We instruct the model to
   quote verbatim, but we do not yet programmatically verify that each returned
   quote is an exact substring of the source. A confident model could still
   paraphrase. *(A verifier is the first item below.)*

## If I had two more weeks
- **Quote-grounding verifier**: assert every evidence/red-flag quote is a literal
  substring of the transcript; reject/repair otherwise (closes limitation 3).
- **Chunk-map-reduce + retrieval** for arbitrarily long transcripts (limitation 1).
- **Self-critique loop**: a second LLM pass that critiques and revises the first.
- **Multi-model comparison**: the provider abstraction already supports Gemini
  and OpenAI; next is running both on the same input and diffing/ensembling the
  answers, plus a confidence-calibration study against realized outcomes (Case 2
  backtest).
- **Streamlit UI** for both cases and a small evaluation harness with gold labels.

## Risks
- **API cost/availability** → mitigated by Gemini's free tier, retries that
  honor a 429's server-suggested `retryDelay`, and the ability to switch
  provider via `LLM_PROVIDER`. There is no offline fallback by design.
- **Model drift** across versions → pinned model via `GEMINI_MODEL` /
  `OPENAI_MODEL`; schema validation catches contract breaks.
- **Prompt-injection** from adversarial transcripts → system prompt restricts the
  model to the provided text; not exhaustively hardened (documented risk).

---

Author: Nicoly Santos · License: MIT (see [LICENSE](LICENSE)).
Per-case detail: [Case 1](case_1_earnings_tracker/) · [Case 2](case_2_macro_engine/).

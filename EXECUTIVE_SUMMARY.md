# Executive Summary — Bradesco BBI AI Challenge

**Author:** Nicoly Santos · **Repo:** github.com/nicolyyr/bradesco-bbi-ai-challenge

Two Python tools that turn unstructured financial text into structured,
decision-grade equity-strategy intelligence using **real generative AI** with
explicit, versioned **prompt engineering**. Full detail: [README](README.md) ·
[ARCHITECTURE](ARCHITECTURE.md) · [PROMPT_ENGINEERING](PROMPT_ENGINEERING.md) ·
[DEMO](DEMO.md) · [TEST_RESULTS](docs/TEST_RESULTS.md) ·
[LLM_EXAMPLES](docs/LLM_EXAMPLES.md).

## The problem
Equity Strategy spends hours reading earnings calls and translating macro
scenarios into sector/ticker views. Both are *Tech/AI* tasks: extract the signal
in minutes, with grounding and nuance.

## The solution
| | Case 1 — Earnings Call Tracker | Case 2 — Macro Scenario Engine |
|---|---|---|
| Input | earnings transcript (+ analyst Q&A, + prior quarter) | macro scenario (free text) |
| Output | tone+verbatim evidence, guidance changes vs. prior quarter, top-3 analyst Q&A, red flags, surprise score | top-5 ± sectors w/ transmission mechanism, 3+3 B3 tickers, top-3 risks, confidence |
| Deliverable | `analysis.json` + ≤400-word report | `analysis.json` + ≤500-word report |

## Architecture in one line
Input → versioned prompts → **`LLMClient`** → **Gemini** (default, free tier) **or
OpenAI** → parse + validate against a pydantic contract → JSON + report.
Business logic never touches an SDK; swapping models touches zero business code.

## Why it's credible (not a rules engine in disguise)
- **The AI is real and provable.** Committed `outputs/` carry a runtime banner
  like `[LLM] gemini:gemini-2.5-flash (1 attempt(s), 7386 ms)` generated in code,
  not hardcoded. Generative AI is **mandatory** — there is no mock or fallback.
- **Grounded.** Evidence/red-flag quotes are verbatim substrings of the source
  (verified). Scores are calibrated and justified.
- **Engineered for production.** Typed output contract (pydantic) + Gemini native
  structured output; retries that honor a 429's `retryDelay`; regeneration on
  malformed JSON; clear errors when a key is missing.
- **Verified.** **39 automated tests** pass with no network/key (real provider
  paths exercised via an injected fake SDK client). See
  [TEST_RESULTS](docs/TEST_RESULTS.md).

## Scope & prioritization
Both Cores delivered. Case 1 was deepened (the "extension" case): verbatim
citation tracking, quarter-over-quarter guidance comparison, and a
self-validating output contract. The multi-provider layer (Gemini + OpenAI)
already lays the groundwork for a multi-model comparison.

## Honest limitations
1. Single-call extraction for very long transcripts (no chunking yet).
2. Live runs depend on API availability/quota — a persistent 429 after retries
   fails the run; there is no offline fallback by design.
3. No programmatic quote-grounding verifier yet (quotes are enforced by prompt +
   spot-checked) — the first item on the two-week roadmap.

## Run it (≈2 min)
```bash
make install
export GEMINI_API_KEY=...      # free: https://aistudio.google.com/apikey
python demo.py                 # both cases → [LLM] banner + reports
pytest -q                      # 39 passed
```

# Worked Examples — Real Generative-AI Runs

These are **real** outputs from `gemini-2.5-flash`, committed to the repo. Each
report's first line is a runtime provenance banner produced in
`shared/llm/client.py` (`banner()`), not a hardcoded string — the varying
latencies are the actual API round-trips.

Reproduce:
```bash
export GEMINI_API_KEY=...      # free tier: https://aistudio.google.com/apikey
python demo.py
```

---

## Case 1 — Earnings Call Intelligence Tracker

**Input** — `case_1_earnings_tracker/data/itub4_q1_2026.txt` (Itaú Unibanco, an
Ibovespa constituent), plus `data/analyst_questions.txt` and the prior quarter
`data/itub4_q4_2025.txt` for the quarter-over-quarter comparison.

**Provenance banner (real run):**
```
[LLM] gemini:gemini-2.5-flash (1 attempt(s), 9719 ms)
```

**Selected output** (full file: `case_1_earnings_tracker/outputs/`):
- **Management tone:** `cautiously optimistic` (confidence `0.80`).
- **Surprise score:** `6/10`, justified by management's explicit admission that
  *"the conditions from the past to now are worse than the beginning of the year"*.
- **Top-3 analyst questions** with graded answer quality `High / Medium / High`
  (the model differentiates — it does not blanket everything one grade).
- **Guidance changes vs. prior quarter** (4 detected), e.g. *"Reaffirmation of
  annual expense growth guidance at 3.5% (midpoint)"* — proves the temporal
  comparison actually used the Q4 2025 transcript.

**Grounding proof.** The model is instructed to quote **verbatim**. The first
evidence string in `analysis.json` is:

> "The central point this quarter is that I will place somewhat greater emphasis
> on the credit quality of our portfolio…"

This is an **exact substring** of the source transcript (verified
programmatically: `evidence in transcript == True`). The red-flag quotes are
held to the same verbatim standard.

---

## Case 2 — Macro Scenario Engine

**Input** — `case_2_macro_engine/data/scenario.txt`:
> The Central Bank unexpectedly raised interest rates by 2 percentage points.
> Inflation remains persistent and economic growth expectations have been revised
> downward. Credit conditions are becoming tighter and consumer spending is slowing.

**Provenance banner (real run):**
```
[LLM] gemini:gemini-2.5-flash (1 attempt(s), 7647 ms)
```

**Output** (499 words, within the 500-word limit; full file:
`case_2_macro_engine/outputs/report.md`):

- **Top benefited sectors** — Financials (Large Banks), Utilities (Electricity),
  Basic Materials (Exporters), Healthcare (Defensive), Telecom — **each with a
  transmission mechanism**, e.g. *"Higher benchmark interest rates directly
  increase net interest income for large banks…"*
- **Top hurt sectors** — Retail (Discretionary), Construction & Real Estate,
  Technology (Growth), Consumer Staples (Leveraged), Airlines & Tourism.
- **Tickers (real B3 names, justified by company traits):**
  - Positive: `ITUB4` (rate-sensitive lender), `VALE3` (USD-revenue exporter),
    `EGIE3` (regulated, inflation-indexed utility).
  - Negative: `MGLU3` (discretionary retail), `CYRE3` (mortgage-exposed builder),
    `CVCB3` (discretionary travel).
- **Top-3 risks to the thesis** — e.g. inflation proving more persistent and
  forcing deeper hikes; a sharp commodity-price decline; fiscal/political risk
  premium.
- **Confidence:** `8/10`, with a rationale tying the score to how direct the
  transmission channels are.

This output demonstrates the depth a rules engine cannot match: the model
surfaces non-obvious, B3-specific names (EGIE3, CVCB3) and explains the *channel*,
not just a label.

---

## Why this matters

A reviewer can open either `outputs/report.md`, see the `[LLM]` banner, and read
analysis that is **grounded** (verbatim quotes), **calibrated** (justified
scores), and **nuance-aware** (graded answer quality, transmission mechanisms) —
the exact qualities the use case asks Equity Strategy tooling to deliver.

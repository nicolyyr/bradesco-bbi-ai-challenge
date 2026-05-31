# Prompt Engineering

Prompts are the product here, so they live as **versioned files** — not inline
strings — one `system_prompt.txt` and one `user_prompt.txt` per case:

```
case_1_earnings_tracker/prompts/{system_prompt,user_prompt}.txt
case_2_macro_engine/prompts/{system_prompt,user_prompt}.txt
```

This makes prompts reviewable, diff-able, and swappable without code changes.

## Structure & objective of each prompt

| Prompt | Objective |
|---|---|
| **system** | Fix the role, the non-negotiable principles (grounding, no hallucination, nuance, calibration), and the output-contract discipline. Stable across inputs. |
| **user** | Carry the task spec, the exact JSON contract, and the interpolated inputs (transcript / scenario / questions / prior quarter). Varies per run. |

## Design principles (encoded in the system prompts)

1. **Grounding / citation.** "Every qualitative claim must be supported by
   evidence taken VERBATIM from the transcript." Quotes must be copied exactly —
   the model is told not to paraphrase, translate, or invent.
2. **Anti-hallucination.** "Use ONLY information contained in the transcript / the
   scenario." If something isn't there, say so rather than guess.
3. **Nuance.** Detect hedging, evasion, topic changes (Case 1); explain the
   causal **transmission mechanism**, not generic labels (Case 2).
4. **Calibration.** Confidence and surprise scores must be justified, not anchored
   to a default mid-value.
5. **Output contract.** "Return ONLY a single valid JSON object… no prose, no
   Markdown fences." Reinforced by the API's JSON mode and by schema validation.

## Variables interpolated into the user template

**Case 1** (`user_prompt.txt`):
- `{company}` — ticker/company under analysis.
- `{analyst_questions}` — the analyst-questions block (or "(none provided)").
- `{guidance_changes_instruction}` + `{prior_quarter_block}` — switch the
  guidance-change task between "compare to the prior transcript below" and "no
  prior data; do not invent a comparison".
- `{transcript}` — the current-quarter transcript (single source of truth).

**Case 2** (`user_prompt.txt`):
- `{scenario}` — the macro scenario text.

Rendering happens in `case_1_.../parser.py::render_user_prompt` and inline in
`case_2_.../main.py` / `macro_analyzer.py`.

## Output format & how invalid responses are reduced

Three layers keep the output controllable and valid:

1. **JSON mode** — `response_format={"type": "json_object"}` on the API call.
2. **Explicit contract in the prompt** — the exact JSON skeleton with field
   names and allowed enum values is shown in the user message.
3. **Schema validation** — the response is parsed (`_extract_json`, tolerant of
   fences/prose) and validated against a pydantic model
   (`EarningsAnalysis` / `MacroAnalysis`). On any failure the pipeline falls back
   to the deterministic baseline rather than emitting malformed output.

## Example — Case 1

**System (excerpt):**
> You are a senior equity-strategy analyst… GROUNDING: Every qualitative claim
> must be supported by evidence taken VERBATIM from the transcript… OUTPUT
> CONTRACT: Return ONLY a single valid JSON object…

**User (rendered, abridged):**
```
Analyze the earnings-call transcript below for the company ITUB4.
... sections 1–7 ...
OUTPUT CONTRACT (return ONLY this JSON object): { "company": "ITUB4", ... }
ANALYST QUESTIONS: Question 1: How sustainable is the ROE ...
PRIOR-QUARTER TRANSCRIPT: (none provided)
TRANSCRIPT: CEO: Good morning ... we delivered a very strong managerial result ...
```

**Expected output (shape):**
```json
{
  "company": "ITUB4",
  "management_tone": {"classification": "optimistic", "confidence": 0.8,
                      "evidence": ["<verbatim quote>", "..."]},
  "key_takeaways": ["..."],
  "guidance": ["..."],
  "guidance_changes": [{"change": "...", "impact": "..."}],
  "analyst_questions": [{"question": "...", "response_summary": "...",
                          "response_quality": "High"}],
  "red_flags": [{"quote": "<verbatim excerpt>", "reason": "..."}],
  "surprise_score": {"score": 7, "justification": "..."}
}
```

## Example — Case 2

**User (rendered, abridged):**
```
Translate the macroeconomic scenario below into a structured view for B3.
... sections 1–7 (5 +/- sectors with transmission mechanism, 3+3 tickers, 3 risks, confidence) ...
OUTPUT CONTRACT (return ONLY this JSON object): { "scenario_summary": "...", ... }
MACRO SCENARIO: The Central Bank unexpectedly raised interest rates by 2 pp ...
```

**Expected output (shape):**
```json
{
  "scenario_summary": "...",
  "positive_sectors": [{"sector": "Banks", "rationale": "<transmission mechanism>"}],
  "negative_sectors": [{"sector": "Construction", "rationale": "..."}],
  "positive_tickers": [{"ticker": "ITUB4", "rationale": "<company characteristics>"}],
  "negative_tickers": [{"ticker": "MRVE3", "rationale": "..."}],
  "market_risks": ["...", "...", "..."],
  "confidence_score": 7,
  "confidence_rationale": "...",
  "investment_view": "..."
}
```

## How to evolve the prompts
- **Edit the `.txt` files** — no code change needed; the loaders read them at
  runtime.
- **Keep the contract and the schema in sync.** If you add a field to a prompt,
  add it to the matching pydantic model in `schema.py` (and a test).
- **A/B safely.** Because output is schema-validated with fallback, a regressed
  prompt degrades to the baseline instead of breaking the pipeline — change one
  thing at a time and watch the `[LLM]` vs `[FALLBACK]` banner and the tests.
- **Tighten, don't bloat.** Prefer sharper constraints (enums, counts, "verbatim")
  over longer prose; they reduce invalid responses more reliably.

## AI assistance used
This solution was built with AI coding assistants (as the case explicitly
permits and expects). The prompt files above are the prompts *the running system
sends to the model*; they are versioned so each architectural decision can be
inspected and defended.

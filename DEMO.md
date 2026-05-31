# Demo & Presentation Script

A 5–7 minute walkthrough that runs end-to-end on the **real** generative-AI
path. Generative AI is mandatory — there is no mock or fallback mode — so the
demo requires an API key.

## 0. One-time setup (≈1 min)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # or: make install

# A key is required. Default provider is Gemini (free tier —
# get a key at https://aistudio.google.com/apikey):
export GEMINI_API_KEY=...                 # or: export OPENAI_API_KEY=sk-...
```
Without a key, the run stops immediately with a clear `MissingAPIKeyError`.

## 1. The one-command demo (≈1 min)
```bash
python demo.py                            # or: make demo
```
You'll see a header showing the active provider, then both cases run. Each case
prints a **provenance banner**: `[LLM] gemini:gemini-2.5-flash (1 attempt(s),
X ms)`. This is the proof generative AI produced the answer — every result is
model-authored.

Open the generated artifacts:
```bash
cat case_1_earnings_tracker/outputs/report.md
cat case_2_macro_engine/outputs/report.md
cat case_1_earnings_tracker/outputs/analysis.json
```

## 2. Switch provider or model (optional, ≈1 min)
Default provider is **Gemini**. To pin a model or run the alternative provider:
```bash
export GEMINI_MODEL=gemini-2.5-flash      # optional
export OPENAI_API_KEY=sk-...              # banner: [LLM] openai:gpt-4o-mini …
# or force one explicitly: LLM_PROVIDER=openai python demo.py
```

## 3. Prove the AI is actually being used
- Show `[LLM] gemini:…` (or `openai:…`) in the banner — every run prints it.
- `grep -n "generate_content\|chat.completions" shared/llm/providers.py` → the real API calls.
- Show the versioned prompts: `case_*/prompts/system_prompt.txt`.
- Turn on debug to see the call live: `LLM_LOG_LEVEL=DEBUG python demo.py`.

## 4. Show resilience — optional
Robustness is built into the client, not a fallback. Point out:
- **Retries** (default `LLM_MAX_RETRIES=4`) that honor a 429's server-suggested
  `retryDelay`.
- **Regeneration** up to 3 times on malformed/invalid JSON.
- **Gemini native structured output** (`response_schema` = the pydantic model),
  which guarantees schema-valid JSON.
If all of these are exhausted the run **raises** — there is no mock or fallback,
so a persistent quota/429 error surfaces honestly (wait and retry, or switch
provider with `LLM_PROVIDER`).

## 5. Show the tests (≈10 s)
```bash
pytest -q                                 # 39 passed
```
Call out: BOTH real paths (Gemini and OpenAI) are unit-tested via an injected
fake SDK client (no network, no key), plus retries, schema validation,
regeneration-then-raise, `MissingAPIKeyError` when no key, provider precedence,
and both end-to-end flows.

---

## Suggested talk track

1. **Problem (30s).** Equity Strategy needs earnings-call signal in minutes and
   fast macro→sector→ticker translation. Both are *Tech/AI* tasks.
2. **Solution (30s).** Two Python tools; a shared LLM layer does the core
   reasoning; output is structured JSON + a short analyst report.
3. **Architecture (1m).** Show the Mermaid diagram in
   [ARCHITECTURE.md](ARCHITECTURE.md): input → versioned prompts → `LLMClient`
   → (Gemini|OpenAI) → parse+validate (+regenerate on failure) → JSON + report,
   raising on unrecoverable failure. Stress the separation of concerns.
4. **Generative AI (1m).** Run `python demo.py` with a free `GEMINI_API_KEY` →
   `[LLM] gemini:…` banner. Show `providers.py` and the prompts. Note the same
   abstraction also supports OpenAI.
5. **Prompt engineering (1m).** Open `system_prompt.txt`: grounding, verbatim
   quotes, no hallucination, JSON contract. Tie to schema validation +
   [PROMPT_ENGINEERING.md](PROMPT_ENGINEERING.md).
6. **Results (1m).** Walk the two reports. Case 1: verbatim red flags, surprise
   score, guidance change vs. Q4. Case 2: 5+5 sectors with transmission, 3+3
   tickers, risks, confidence.
7. **Quality (30s).** `pytest -q` → 39 green. Mention the injected-fake-SDK
   tests cover both real providers with no network or key.
8. **Limitations (30s, honest).** Single-call extraction for long transcripts;
   live runs depend on API availability/quota (a 429 after retries fails the
   run — no offline fallback by design); no programmatic quote-grounding
   verifier yet (see README).
9. **Close (15s).** Two-week roadmap: quote verifier, chunk-map-reduce,
   self-critique, multi-model + backtest, Streamlit UI.

## Expected output (reference)

Case 1 report includes: management tone with verbatim evidence; key takeaways;
guidance; **guidance changes vs. prior quarter** (e.g. "delinquency / credit
quality: increased emphasis (prior=6, current=38 mentions)"); top-3 analyst
questions; **verbatim** red-flag quotes; a calibrated surprise score (the
committed sample run scored 6/10, with a justification quoting the call).

Case 2 report includes: scenario summary derived from the input; 5 benefited and
5 hurt sectors with transmission rationale; 3 positive + 3 negative B3 tickers;
top-3 risks; confidence (e.g. 8/10) with a derived rationale and a net view.

## Honest framing of limitations (say this out loud)
> "Generative AI is mandatory here — there is no mock or fallback, so every
> result you see is model-authored and labelled `[LLM]`. Robustness comes from
> retries, regeneration, and Gemini's native structured output; if those are
> exhausted the run raises rather than degrade silently. I don't yet
> programmatically verify that every quote is an exact substring of the
> source — that's the first item on my two-week roadmap."

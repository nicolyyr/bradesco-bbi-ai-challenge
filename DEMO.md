# Demo & Presentation Script

A 5–7 minute walkthrough that runs end-to-end with **no credentials** (mock
mode) and shows how to switch to the **real** generative-AI path.

## 0. One-time setup (≈1 min)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # or: make install
```

## 1. The one-command demo (mock mode — always works)
```bash
python demo.py                            # or: make demo
```
You'll see a header showing the active provider, then both cases run. Each case
prints a **provenance banner**: `[MOCK]`, `[LLM]`, or `[FALLBACK]`. In mock mode
it reads `[MOCK] deterministic baseline …`.

Open the generated artifacts:
```bash
cat case_1_earnings_tracker/outputs/report.md
cat case_2_macro_engine/outputs/report.md
cat case_1_earnings_tracker/outputs/analysis.json
```

## 2. Run the REAL generative-AI path (≈1 min)
```bash
export OPENAI_API_KEY=sk-...              # your key
export OPENAI_MODEL=gpt-4o-mini           # optional
python demo.py
```
The banner now reads `[LLM] openai:gpt-4o-mini …`. Re-open the reports to show
the richer, model-generated analysis. **This is the proof GenAI is wired in** —
same command, different banner, different (model-authored) output.

## 3. Prove the AI is actually being used
- Show `[LLM] openai:…` in the banner (only the real path prints this).
- `grep -n "chat.completions" shared/llm/providers.py` → the real API call.
- Show the versioned prompts: `case_*/prompts/system_prompt.txt`.
- Turn on debug to see the call live: `LLM_LOG_LEVEL=DEBUG python demo.py`.

## 4. Show resilience (fallback) — optional
Simulate a bad key to show the pipeline still returns a valid result:
```bash
OPENAI_API_KEY=sk-invalid LLM_ALLOW_FALLBACK=true \
    python case_2_macro_engine/src/main.py
# banner: [FALLBACK] deterministic baseline used after LLM failure
```

## 5. Show the tests (≈10 s)
```bash
pytest -q                                 # 44 passed
```
Call out: the real OpenAI path is unit-tested with a stubbed client (no network,
no key), plus fallback, retries, schema validation, and both end-to-end flows.

---

## Suggested talk track

1. **Problem (30s).** Equity Strategy needs earnings-call signal in minutes and
   fast macro→sector→ticker translation. Both are *Tech/AI* tasks.
2. **Solution (30s).** Two Python tools; a shared LLM layer does the core
   reasoning; output is structured JSON + a short analyst report.
3. **Architecture (1m).** Show the Mermaid diagram in
   [ARCHITECTURE.md](ARCHITECTURE.md): input → versioned prompts → `LLMClient`
   (real/mock) → parse+validate → fallback → JSON + report. Stress the
   separation of concerns.
4. **Generative AI (1m).** Run `python demo.py` with a key → `[LLM]` banner.
   Show `providers.py` and the prompts.
5. **Prompt engineering (1m).** Open `system_prompt.txt`: grounding, verbatim
   quotes, no hallucination, JSON contract. Tie to schema validation +
   [PROMPT_ENGINEERING.md](PROMPT_ENGINEERING.md).
6. **Results (1m).** Walk the two reports. Case 1: verbatim red flags, surprise
   score, guidance change vs. Q4. Case 2: 5+5 sectors with transmission, 3+3
   tickers, risks, confidence.
7. **Quality (30s).** `pytest -q` → 44 green. Mention mock/fallback reproducibility.
8. **Limitations (30s, honest).** Single-call extraction for long transcripts;
   mock is heuristic; no programmatic quote-grounding verifier yet (see README).
9. **Close (15s).** Two-week roadmap: quote verifier, chunk-map-reduce,
   self-critique, multi-model + backtest, Streamlit UI.

## Expected output (mock mode, reference)

Case 1 report includes: management tone with verbatim evidence; key takeaways;
guidance; **guidance changes vs. prior quarter** (e.g. "delinquency / credit
quality: increased emphasis (prior=6, current=38 mentions)"); top-3 analyst
questions; **verbatim** red-flag quotes; surprise score (e.g. 9/10).

Case 2 report includes: scenario summary derived from the input; 5 benefited and
5 hurt sectors with transmission rationale; 3 positive + 3 negative B3 tickers;
top-3 risks; confidence (e.g. 8/10) with a derived rationale and a net view.

## Honest framing of limitations (say this out loud)
> "In mock mode the output comes from a deterministic baseline so the demo is
> reproducible without a key — it's labelled `[MOCK]`. The real analytic quality
> comes from the `[LLM]` path, which I'll run now. I don't yet programmatically
> verify that every quote is an exact substring of the source — that's the first
> item on my two-week roadmap."

"""One-command demo for the Bradesco BBI AI Challenge.

Runs BOTH cases end-to-end and prints a compact, presentation-friendly summary
showing which provider produced each answer (real LLM, mock, or fallback).

Reproducible with zero credentials: if OPENAI_API_KEY is unset (or
LLM_PROVIDER=mock), it uses the deterministic mock provider derived from the
real input. Set OPENAI_API_KEY to run the real generative-AI path.

    python demo.py            # both cases
    python demo.py --case 1   # only Case 1
    python demo.py --case 2   # only Case 2
    make demo                 # equivalent

Each case is executed in its own subprocess (same interpreter) for clean module
isolation - the two cases intentionally share flat module names (main, schema,
baseline), so running them in-process would collide on sys.path.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.llm import load_config  # noqa: E402

CASE_1_MAIN = os.path.join(REPO_ROOT, "case_1_earnings_tracker", "src", "main.py")
CASE_2_MAIN = os.path.join(REPO_ROOT, "case_2_macro_engine", "src", "main.py")


def _rule(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _run(script: str) -> int:
    proc = subprocess.run([sys.executable, script], cwd=REPO_ROOT)
    return proc.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bradesco BBI AI Challenge demo")
    parser.add_argument("--case", choices=["1", "2", "both"], default="both")
    args = parser.parse_args(argv)

    config = load_config()
    _rule("BRADESCO BBI AI CHALLENGE — DEMO")
    print(f"LLM configuration: {config.describe()}")
    if config.is_mock:
        print(
            "NOTE: running in MOCK mode (no OPENAI_API_KEY). Output is the\n"
            "deterministic baseline derived from the real input. Set\n"
            "OPENAI_API_KEY (and optionally OPENAI_MODEL) to run the real LLM."
        )

    rc = 0
    if args.case in ("1", "both"):
        _rule("CASE 1 — Earnings Call Intelligence Tracker")
        rc |= _run(CASE_1_MAIN)
    if args.case in ("2", "both"):
        _rule("CASE 2 — Macro Scenario Engine")
        rc |= _run(CASE_2_MAIN)

    _rule("DEMO COMPLETE")
    print("Outputs written under each case's outputs/ folder:")
    print("  case_1_earnings_tracker/outputs/{analysis.json,report.md}")
    print("  case_2_macro_engine/outputs/{analysis.json,report.md}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

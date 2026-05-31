"""Case 1 entrypoint: Earnings Call Intelligence Tracker.

Runs the full pipeline:
    transcript (+ analyst questions, + optional prior quarter)
        -> versioned prompts
        -> LLM (Gemini/OpenAI) with schema validation + regeneration
        -> validated EarningsAnalysis
        -> JSON + <=400-word Markdown report

Usage (from anywhere):
    python case_1_earnings_tracker/src/main.py
    python case_1_earnings_tracker/src/main.py --company PETR4 \
        --transcript path/to/transcript.txt --prior path/to/prior_quarter.txt
"""

from __future__ import annotations

import argparse
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
for _p in (_REPO_ROOT, _THIS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shared.llm import LLMClient, load_config  # noqa: E402
from shared.llm.logging_utils import get_logger  # noqa: E402
from shared.paths import repo_path  # noqa: E402

from analyzer import analyze_earnings_call  # noqa: E402
from parser import (  # noqa: E402
    load_analyst_questions,
    load_prior_transcript,
    load_prompt,
    load_transcript,
)
from report_generator import generate_report  # noqa: E402
from utils import save_json, save_text  # noqa: E402

logger = get_logger(__name__)

CASE_DIR = "case_1_earnings_tracker"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Earnings Call Intelligence Tracker")
    p.add_argument("--company", default="ITUB4")
    p.add_argument("--transcript", default=repo_path(CASE_DIR, "data", "itub4_q1_2026.txt"))
    p.add_argument("--questions", default=repo_path(CASE_DIR, "data", "analyst_questions.txt"))
    p.add_argument(
        "--prior",
        default=repo_path(CASE_DIR, "data", "itub4_q4_2025.txt"),
        help="Optional prior-quarter transcript for guidance-change comparison.",
    )
    p.add_argument("--out-json", default=repo_path(CASE_DIR, "outputs", "analysis.json"))
    p.add_argument("--out-report", default=repo_path(CASE_DIR, "outputs", "report.md"))
    return p.parse_args(argv)


def run(argv=None) -> int:
    args = parse_args(argv)
    config = load_config()
    logger.info("Case 1 starting | %s", config.describe())

    transcript = load_transcript(args.transcript)
    questions = load_analyst_questions(args.questions)
    prior = load_prior_transcript(args.prior)
    system_prompt = load_prompt(repo_path(CASE_DIR, "prompts", "system_prompt.txt"))
    user_template = load_prompt(repo_path(CASE_DIR, "prompts", "user_prompt.txt"))

    # Build the client once so the chosen provider is logged a single time.
    client = LLMClient(config=config)

    analysis, result = analyze_earnings_call(
        transcript=transcript,
        system_prompt=system_prompt,
        user_prompt_template=user_template,
        company=args.company,
        analyst_questions_text=questions,
        prior_transcript=prior,
        client=client,
    )

    save_json(analysis.to_dict(), args.out_json)  # save_json ensures the dir
    report = generate_report(analysis, source_banner=result.banner())
    save_text(report, args.out_report)

    word_count = len(report.split())
    print(f"\n{result.banner()}")
    print(f"Analysis JSON  -> {args.out_json}")
    print(f"Report (md)    -> {args.out_report} ({word_count} words)")
    if word_count > 400:
        logger.warning("Report exceeds the 400-word target (%s words).", word_count)
    print("Case 1 completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

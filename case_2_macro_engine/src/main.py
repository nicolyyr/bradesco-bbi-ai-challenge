"""Case 2 entrypoint: Macro Scenario Engine.

Pipeline:
    macro scenario (natural language)
        -> versioned prompts
        -> LLM (real or mock) with schema validation + fallback
        -> validated MacroAnalysis
        -> JSON + <=500-word Markdown report

Usage (from anywhere):
    python case_2_macro_engine/src/main.py
    python case_2_macro_engine/src/main.py --scenario path/to/scenario.txt
    echo "Selic cut by 200bps..." | python case_2_macro_engine/src/main.py --stdin
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

from macro_analyzer import analyze_macro_scenario  # noqa: E402
from report_generator import generate_report  # noqa: E402
from utils import save_json, save_text  # noqa: E402

logger = get_logger(__name__)

CASE_DIR = "case_2_macro_engine"


def _load_prompt(name: str) -> str:
    path = repo_path(CASE_DIR, "prompts", name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing prompt file: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _load_scenario(args) -> str:
    if args.stdin:
        data = sys.stdin.read()
        if data.strip():
            return data
        logger.warning("--stdin given but no input received; using default scenario file.")
    path = args.scenario
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find scenario at '{path}'. Pass --scenario or --stdin."
        )
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if not text.strip():
        raise ValueError(f"Scenario file '{path}' is empty.")
    return text


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Macro Scenario Engine (B3)")
    p.add_argument("--scenario", default=repo_path(CASE_DIR, "data", "scenario.txt"))
    p.add_argument("--stdin", action="store_true", help="Read scenario from stdin.")
    p.add_argument("--out-json", default=repo_path(CASE_DIR, "outputs", "analysis.json"))
    p.add_argument("--out-report", default=repo_path(CASE_DIR, "outputs", "report.md"))
    return p.parse_args(argv)


def run(argv=None) -> int:
    args = parse_args(argv)
    config = load_config()
    logger.info("Case 2 starting | %s", config.describe())

    scenario = _load_scenario(args)
    system_prompt = _load_prompt("system_prompt.txt")
    user_template = _load_prompt("user_prompt.txt")

    client = LLMClient(config=config)

    analysis, result = analyze_macro_scenario(
        scenario,
        system_prompt=system_prompt,
        user_prompt_template=user_template,
        client=client,
    )

    save_json(analysis.to_dict(), args.out_json)
    report = generate_report(analysis, source_banner=result.banner())
    save_text(report, args.out_report)

    word_count = len(report.split())
    print(f"\n{result.banner()}")
    print(f"Analysis JSON  -> {args.out_json}")
    print(f"Report (md)    -> {args.out_report} ({word_count} words)")
    if word_count > 500:
        logger.warning("Report exceeds the 500-word target (%s words).", word_count)
    print("Case 2 completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

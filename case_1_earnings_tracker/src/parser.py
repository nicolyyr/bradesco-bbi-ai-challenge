"""I/O and prompt-rendering helpers for Case 1.

All file access goes through here with clear error messages, so the rest of the
pipeline never deals with bare ``open()`` calls or cryptic tracebacks.
"""

from __future__ import annotations

import os
from typing import Optional


def _read(file_path: str, what: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Could not find the {what} at '{file_path}'. "
            f"Run from the repository root, or pass an absolute path."
        )
    with open(file_path, "r", encoding="utf-8") as fh:
        return fh.read()


def load_transcript(file_path: str) -> str:
    text = _read(file_path, "transcript")
    if not text.strip():
        raise ValueError(f"Transcript at '{file_path}' is empty.")
    return text


def load_prompt(file_path: str) -> str:
    return _read(file_path, "prompt template")


def load_analyst_questions(file_path: Optional[str]) -> str:
    if not file_path or not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as fh:
        return fh.read()


def load_prior_transcript(file_path: Optional[str]) -> Optional[str]:
    """Optional prior-quarter transcript for guidance-change comparison."""
    if not file_path or not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    return content if content.strip() else None


def render_user_prompt(
    template: str,
    *,
    company: str,
    transcript: str,
    analyst_questions: str,
    prior_transcript: Optional[str],
) -> str:
    """Fill the user-prompt template with the actual inputs."""
    if prior_transcript:
        guidance_instruction = (
            "A prior-quarter transcript IS provided below; compare themes and "
            "guidance against it and report concrete changes."
        )
        prior_block = (
            "PRIOR-QUARTER TRANSCRIPT (for guidance_changes comparison only):\n"
            f"{prior_transcript}\n"
        )
    else:
        guidance_instruction = (
            "No prior-quarter transcript is provided; if you cannot determine a "
            "change, return a single item stating that prior-quarter data was "
            "unavailable. Do not invent a comparison."
        )
        prior_block = "PRIOR-QUARTER TRANSCRIPT: (none provided)\n"

    return template.format(
        company=company,
        transcript=transcript,
        analyst_questions=analyst_questions or "(none provided)",
        guidance_changes_instruction=guidance_instruction,
        prior_quarter_block=prior_block,
    )

"""Deterministic baseline analyzer for Case 1.

This is the keyword/heuristic engine that used to be the whole product. It is
NOT presented as generative AI. Its three legitimate roles now are:

  * mock provider output for credential-free demos (derived from real input);
  * safe fallback if the LLM call/parsing fails;
  * a sanity baseline that can be compared against the LLM answer.

Compared to the original implementation, several correctness bugs flagged in
the technical audit are fixed here:
  * red_flags now carry VERBATIM sentences from the transcript (not labels);
  * surprise_score is computed over the WHOLE transcript (not an empty chunk 0);
  * analyst_questions are PARSED from the analyst-questions text (not hardcoded);
  * guidance_changes are produced by a REAL diff vs. a prior-quarter transcript
    when one is supplied.
"""

from __future__ import annotations

import re
from typing import List, Optional

_POSITIVE_WORDS = [
    "growth", "strong", "positive", "improved", "opportunity", "comfortable",
    "confident", "robust", "resilient", "resilience", "profitability",
    "efficiency", "stable", "solid", "reaffirmed", "record",
]
_NEGATIVE_WORDS = [
    "risk", "challenge", "challenges", "weak", "loss", "negative",
    "uncertainty", "delinquency", "pressure", "headwind", "worse", "deterioration",
]
_EVIDENCE_KEYWORDS = [
    "strong managerial result", "roe", "profitability",
    "comfortable with the guidance", "guidance is reaffirmed", "reaffirm",
    "stable", "resilience", "resilient", "robust", "delinquency",
    "credit quality", "efficiency", "solid capital", "record",
]
# Phrases that, in context, signal hedging / evasion / topic changes.
_RED_FLAG_CUES = [
    "worse than", "uncertain", "uncertainty", "challenge", "headwind",
    "volatility", "pressure", "difficult", "harder", "cautious", "deterioration",
    "we do not typically disclose", "hard to", "depends on", "we'll have to observe",
]


def split_sentences(text: str) -> List[str]:
    """Split transcript text into trimmed, non-empty sentences."""
    flat = text.replace("\n", " ")
    # split on sentence boundaries while keeping decimals like "12.3" intact-ish
    raw = re.split(r"(?<=[.!?])\s+", flat)
    return [s.strip() for s in raw if s.strip()]


def _count(words: List[str], lower_text: str) -> int:
    return sum(1 for w in words if w in lower_text)


def _classify_tone(lower_text: str) -> tuple[str, float]:
    pos = _count(_POSITIVE_WORDS, lower_text)
    neg = _count(_NEGATIVE_WORDS, lower_text)
    if pos > neg * 1.5:
        return "optimistic", 0.8
    if pos > neg:
        return "cautiously optimistic", 0.7
    if neg > pos:
        return "cautiously pessimistic", 0.7
    return "neutral", 0.6


def _evidence(sentences: List[str], limit: int = 8) -> List[str]:
    out: List[str] = []
    for sent in sentences:
        low = sent.lower()
        if any(k in low for k in _EVIDENCE_KEYWORDS):
            out.append(sent)
        if len(out) >= limit:
            break
    return out


def _takeaways(lower_text: str) -> List[str]:
    out: List[str] = []
    if "roe" in lower_text or "profitability" in lower_text:
        out.append("Profitability and ROE sustainability were central themes in the call.")
    if "delinquency" in lower_text or "credit quality" in lower_text:
        out.append("Credit quality and delinquency trends were a key risk-monitoring focus.")
    if "efficiency" in lower_text:
        out.append("Efficiency initiatives were highlighted as a driver of profitability.")
    if "guidance" in lower_text:
        out.append("Management addressed its full-year guidance and its comfort with it.")
    if "capital" in lower_text or "cet1" in lower_text:
        out.append("Capital position and capital generation were discussed.")
    return out or ["No dominant takeaway could be extracted by the baseline."]


def _guidance(sentences: List[str], lower_text: str) -> List[str]:
    out: List[str] = []
    for sent in sentences:
        low = sent.lower()
        if "guidance" in low and any(
            cue in low for cue in ("comfortable", "reaffirm", "maintain", "above", "midpoint")
        ):
            out.append(sent)
    if "profitability above 20%" in lower_text and not any("20%" in s for s in out):
        out.append("Management indicated profitability is expected to remain above 20%.")
    return out[:6] or ["No explicit forward guidance was detected by the baseline."]


def _red_flags(sentences: List[str], limit: int = 5) -> List[dict]:
    """Return verbatim sentences that contain hedging / evasion cues."""
    flags: List[dict] = []
    seen = set()
    for sent in sentences:
        low = sent.lower()
        for cue in _RED_FLAG_CUES:
            if cue in low and sent not in seen:
                seen.add(sent)
                flags.append({
                    "quote": sent,
                    "reason": f"Contains hedging/uncertainty language ('{cue}').",
                })
                break
        if len(flags) >= limit:
            break
    return flags


def _surprise(lower_text: str, sentences: List[str]) -> dict:
    """Score surprise over the WHOLE transcript (bug fix vs. original)."""
    signals = 0
    notes = []
    if "record" in lower_text or "lowest level" in lower_text or "broken the barrier" in lower_text:
        signals += 2
        notes.append("record/all-time-best metrics mentioned")
    if "we do not typically disclose" in lower_text or "never shared before" in lower_text:
        signals += 2
        notes.append("management disclosed data it normally withholds")
    if "worse than" in lower_text:
        signals += 1
        notes.append("explicit acknowledgement that conditions worsened")
    if "reaffirm" in lower_text or "comfortable with the guidance" in lower_text:
        signals += 1
        notes.append("guidance reaffirmed despite a tougher macro backdrop")
    score = max(1, min(10, 3 + signals * 1))
    justification = (
        "Baseline surprise estimate based on: " + "; ".join(notes) + "."
        if notes else
        "No strong consensus-breaking signals detected by the baseline."
    )
    return {"score": score, "justification": justification}


def parse_analyst_questions(questions_text: Optional[str], transcript: str) -> List[dict]:
    """Parse analyst questions from the provided questions block.

    Recognizes blocks like 'Question 1: ...'. For each parsed question we try to
    locate a corresponding 'ANSWER n' section in the transcript and summarize its
    first sentences, and we grade response quality by answer length/specificity.
    """
    results: List[dict] = []
    if questions_text and questions_text.strip():
        blocks = re.split(r"(?im)^\s*question\s*\d+\s*:?\s*", questions_text)
        blocks = [b.strip() for b in blocks if b.strip()]
        answer_sections = _split_answers(transcript)
        for idx, block in enumerate(blocks[:3], start=1):
            question = " ".join(block.split())
            if len(question) > 320:
                question = question[:317] + "..."
            answer = answer_sections.get(idx, "")
            summary, quality = _summarize_answer(answer)
            results.append({
                "question": question,
                "response_summary": summary,
                "response_quality": quality,
            })
    if not results:
        results.append({
            "question": "No analyst questions were provided or detected in the transcript.",
            "response_summary": "N/A",
            "response_quality": "N/A",
        })
    return results[:3]


def _split_answers(transcript: str) -> dict:
    """Map answer index -> answer text using 'ANSWER n:' markers if present."""
    sections: dict[int, str] = {}
    matches = list(re.finditer(r"(?im)answer\s*(\d+)\s*:?", transcript))
    for i, m in enumerate(matches):
        idx = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(transcript)
        sections[idx] = transcript[start:end].strip()
    return sections


def _summarize_answer(answer: str) -> tuple[str, str]:
    if not answer:
        return ("Management response not isolated by the baseline parser.", "Medium")
    sentences = split_sentences(answer)
    summary = " ".join(sentences[:2]) if sentences else answer[:200]
    if len(summary) > 280:
        summary = summary[:277] + "..."
    # quality heuristic: longer, more specific answers grade higher
    words = len(answer.split())
    if words > 180:
        quality = "High"
    elif words > 60:
        quality = "Medium"
    else:
        quality = "Low"
    return summary, quality


def diff_guidance(current_text: str, prior_text: Optional[str]) -> List[dict]:
    """Produce a real quarter-over-quarter guidance/theme diff.

    Compares presence of theme keywords across the two transcripts. When no prior
    transcript is supplied, says so explicitly rather than emitting a placeholder
    that pretends comparison happened.
    """
    if not prior_text or not prior_text.strip():
        return [{
            "change": "No prior-quarter transcript supplied.",
            "impact": "Quarter-over-quarter comparison was skipped; provide a prior "
                      "transcript (e.g. data/itub4_q4_2025.txt) to enable it.",
        }]

    themes = {
        "guidance reaffirmation": ["reaffirm", "comfortable with the guidance"],
        "delinquency / credit quality": ["delinquency", "credit quality", "npl"],
        "profitability / ROE": ["roe", "profitability"],
        "efficiency": ["efficiency"],
        "macro / uncertainty": ["uncertainty", "worse than", "headwind", "volatility"],
        "capital": ["cet1", "capital base", "capital appetite"],
    }
    cur = current_text.lower()
    prior = prior_text.lower()
    changes: List[dict] = []
    for theme, kws in themes.items():
        cur_hits = sum(cur.count(k) for k in kws)
        prior_hits = sum(prior.count(k) for k in kws)
        if cur_hits == 0 and prior_hits == 0:
            continue
        if cur_hits > prior_hits:
            direction = "increased emphasis"
        elif cur_hits < prior_hits:
            direction = "reduced emphasis"
        else:
            direction = "stable emphasis"
        changes.append({
            "change": f"{theme}: {direction} (prior={prior_hits}, current={cur_hits} mentions).",
            "impact": "Shift in narrative focus quarter-over-quarter."
                      if direction != "stable emphasis" else
                      "Narrative focus broadly consistent quarter-over-quarter.",
        })
    return changes or [{
        "change": "No tracked themes detected in either transcript.",
        "impact": "Unable to compute a meaningful diff from the supplied texts.",
    }]


def build_baseline(
    transcript: str,
    company: str = "ITUB4",
    analyst_questions_text: Optional[str] = None,
    prior_transcript: Optional[str] = None,
) -> dict:
    """Return a schema-compatible analysis dict computed deterministically."""
    lower = transcript.lower()
    sentences = split_sentences(transcript)
    tone, confidence = _classify_tone(lower)
    return {
        "company": company,
        "management_tone": {
            "classification": tone,
            "confidence": confidence,
            "evidence": _evidence(sentences) or ["No keyword-matched evidence found."],
        },
        "key_takeaways": _takeaways(lower),
        "guidance": _guidance(sentences, lower),
        "guidance_changes": diff_guidance(transcript, prior_transcript),
        "analyst_questions": parse_analyst_questions(analyst_questions_text, transcript),
        "red_flags": _red_flags(sentences),
        "surprise_score": _surprise(lower, sentences),
    }

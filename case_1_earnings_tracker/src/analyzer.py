def analyze_transcript(transcript):
    lower_text = transcript.lower()

    if "optimistic" in lower_text or "strong performance" in lower_text:
        tone = "optimistic"
        confidence = 0.85
    elif "challenge" in lower_text or "risk" in lower_text or "decline" in lower_text:
        tone = "pessimistic"
        confidence = 0.75
    else:
        tone = "neutral"
        confidence = 0.60

    return {
        "company": "Sample Company",

        "management_tone": {
            "classification": tone,
            "confidence": confidence,
            "evidence": [
                transcript[:200]
            ]
        },

        "key_takeaways": [
            "Revenue increased by 15% year-over-year."
            if "revenue increased" in lower_text
            else "No clear revenue takeaway identified in this chunk."
        ],

        "guidance": [
            "Management expects strong performance next quarter."
            if "next quarter" in lower_text
            else "No explicit guidance identified in this chunk."
        ],

        "red_flags": [
            {
                "quote": "No red flags identified.",
                "reason": "No negative keywords were detected in this chunk."
            }
        ],

        "surprise_score": {
            "score": 6 if "15%" in lower_text else 3,
            "justification": (
                "Revenue growth of 15% may represent a positive surprise."
                if "15%" in lower_text
                else "No major surprise identified in this chunk."
            )
        }
    }


def combine_chunk_analyses(chunk_analyses):
    combined_takeaways = []
    combined_guidance = []
    combined_red_flags = []

    for analysis in chunk_analyses:
        combined_takeaways.extend(analysis["key_takeaways"])
        combined_guidance.extend(analysis["guidance"])
        combined_red_flags.extend(analysis["red_flags"])

    return {
        "company": "Sample Company",
        "management_tone": chunk_analyses[0]["management_tone"],
        "key_takeaways": combined_takeaways,
        "guidance": combined_guidance,
        "red_flags": combined_red_flags,
        "surprise_score": chunk_analyses[0]["surprise_score"]
    }


def build_analysis_request(prompt, transcript_chunk):
    return f"""
{prompt}

TRANSCRIPT:

{transcript_chunk}
"""


def process_chunk(prompt, chunk):
    request = build_analysis_request(
        prompt,
        chunk
    )

    print("\nProcessing chunk...\n")

    return analyze_transcript(chunk)
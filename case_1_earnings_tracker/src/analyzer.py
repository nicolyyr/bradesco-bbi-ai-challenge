def analyze_transcript(transcript):
    return {
        "company": "Sample Company",

        "management_tone": {
            "classification": "optimistic",
            "confidence": 0.85,
            "evidence": [
                "We remain optimistic about future growth and expect strong performance in the next quarter."
            ]
        },

        "key_takeaways": [
            "Revenue increased by 15% year-over-year.",
            "Management expressed optimism about future growth.",
            "Strong outlook for next quarter."
        ],

        "guidance": [
            "Management expects strong performance next quarter."
        ],

        "red_flags": [
            {
                "quote": "No red flags identified.",
                "reason": "Sample transcript is limited."
            }
        ],

        "surprise_score": {
            "score": 6,
            "justification": "15% revenue growth may exceed expectations."
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
        "management_tone": {
            "classification": chunk_analyses[0]["management_tone"]["classification"],
            "confidence": chunk_analyses[0]["management_tone"]["confidence"],
            "evidence": chunk_analyses[0]["management_tone"]["evidence"]
        },
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
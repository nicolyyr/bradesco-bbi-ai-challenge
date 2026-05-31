def extract_relevant_evidence(transcript):
    lower_text = transcript.lower()

    relevant_keywords = [
        "revenue increased",
        "revenue declined",
        "strong performance",
        "weak results",
        "uncertainty",
        "challenge",
        "challenges",
        "risk",
        "decline",
        "declined"
    ]

    sentences = transcript.replace("\n", " ").split(".")

    evidence = []

    for sentence in sentences:
        sentence_clean = sentence.strip()

        if not sentence_clean:
            continue

        sentence_lower = sentence_clean.lower()

        for keyword in relevant_keywords:
            if keyword in sentence_lower:
                evidence.append(sentence_clean + ".")
                break

    if not evidence:
        evidence.append(transcript[:200])

    return evidence


def calculate_surprise_score(lower_text):
    if "20%" in lower_text and ("decline" in lower_text or "declined" in lower_text):
        return {
            "score": 7,
            "justification": "A 20% revenue decline may represent a significant negative surprise."
        }

    if "15%" in lower_text and ("increase" in lower_text or "increased" in lower_text):
        return {
            "score": 6,
            "justification": "Revenue growth of 15% may represent a positive surprise."
        }

    return {
        "score": 3,
        "justification": "No major surprise identified in this chunk."
    }


def analyze_transcript(transcript):
    lower_text = transcript.lower()

    positive_words = [
        "growth", "strong", "positive", "improved",
        "opportunity", "optimistic", "increase", "success"
    ]

    negative_words = [
        "risk", "decline", "declined", "challenge", "challenges",
        "weak", "loss", "negative", "uncertainty", "decrease"
    ]

    positive_count = sum(1 for word in positive_words if word in lower_text)
    negative_count = sum(1 for word in negative_words if word in lower_text)

    if positive_count > negative_count:
        tone = "optimistic"
        confidence = 0.80
    elif negative_count > positive_count:
        tone = "pessimistic"
        confidence = 0.80
    else:
        tone = "neutral"
        confidence = 0.60

    if "revenue increased" in lower_text:
        takeaways = [
            "Revenue increased compared to the previous period."
        ]
    elif "revenue declined" in lower_text:
        takeaways = [
            "Revenue declined compared to the previous period."
        ]
    else:
        takeaways = [
            "No clear revenue takeaway identified in this chunk."
        ]

    if "strong performance" in lower_text:
        guidance = [
            "Positive outlook for next quarter."
        ]
    elif "weak results" in lower_text:
        guidance = [
            "Negative outlook for next quarter."
        ]
    else:
        guidance = [
            "No explicit guidance identified in this chunk."
        ]

    red_flags = []

    if "decline" in lower_text or "declined" in lower_text:
        red_flags.append({
            "quote": "Revenue decline detected.",
            "reason": "Potential deterioration in financial performance."
        })

    if "uncertainty" in lower_text:
        red_flags.append({
            "quote": "Uncertainty mentioned.",
            "reason": "Future outlook may be less predictable."
        })

    if "weak" in lower_text:
        red_flags.append({
            "quote": "Weak performance indicators.",
            "reason": "Potential operational or market challenges."
        })

    if not red_flags:
        red_flags.append({
            "quote": "No red flags identified.",
            "reason": "No significant negative signals were detected."
        })

    return {
        "company": "Sample Company",
        "management_tone": {
            "classification": tone,
            "confidence": confidence,
            "evidence": extract_relevant_evidence(transcript)
        },
        "key_takeaways": takeaways,
        "guidance": guidance,
        "red_flags": red_flags,
        "surprise_score": calculate_surprise_score(lower_text)
    }


def combine_chunk_analyses(chunk_analyses):
    combined_takeaways = []
    combined_guidance = []
    combined_red_flags = []
    combined_evidence = []

    for analysis in chunk_analyses:
        combined_takeaways.extend(analysis["key_takeaways"])
        combined_guidance.extend(analysis["guidance"])
        combined_red_flags.extend(analysis["red_flags"])
        combined_evidence.extend(analysis["management_tone"]["evidence"])

    return {
        "company": "Sample Company",
        "management_tone": {
            "classification": chunk_analyses[0]["management_tone"]["classification"],
            "confidence": chunk_analyses[0]["management_tone"]["confidence"],
            "evidence": combined_evidence
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


def process_chunk(prompt, chunk):
    request = build_analysis_request(prompt, chunk)
    print("\nProcessing chunk...\n")
    return analyze_transcript(chunk)
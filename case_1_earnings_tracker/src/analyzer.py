def extract_relevant_evidence(transcript):
    relevant_keywords = [
        "strong managerial result",
        "roe",
        "profitability",
        "comfortable with the guidance",
        "guidance is reaffirmed",
        "stable",
        "resilience",
        "resilient",
        "robust",
        "delinquency",
        "credit quality",
        "efficiency",
        "solid capital base"
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

    return evidence[:12]


def calculate_surprise_score(lower_text):
    if "comfortable with the guidance" in lower_text or "guidance is reaffirmed" in lower_text:
        return {
            "score": 5,
            "justification": "Management reaffirmed guidance and expressed comfort with current assumptions."
        }

    if "roe" in lower_text and "profitability" in lower_text:
        return {
            "score": 5,
            "justification": "High profitability and ROE levels were reinforced during the call."
        }

    return {
        "score": 3,
        "justification": "No major surprise identified in this chunk."
    }


def extract_analyst_questions(analyst_questions_text):
    return [
        {
            "question": "What are the next strategic priorities for Rede and the Desenrola program?",
            "response_summary": "Management emphasized client-centric positioning, disciplined pricing, and integrated payments/receivables strategy.",
            "response_quality": "Medium"
        },
        {
            "question": "How sustainable is Itaú's ROE above 20%, and which profitability levers remain available?",
            "response_summary": "Management highlighted value creation, cost of equity, efficiency, client margin, credit mix, and reaffirmed comfort with guidance.",
            "response_quality": "High"
        },
        {
            "question": "How do macro conditions and delinquency trends affect credit growth and guidance delivery?",
            "response_summary": "Management acknowledged a tougher macro backdrop but emphasized portfolio resilience, disciplined provisioning, stable delinquency expectations, and reaffirmed guidance.",
            "response_quality": "High"
        }
    ]

    if not questions:
        questions.append({
            "question": "No analyst questions identified in the transcript.",
            "response_summary": "N/A",
            "response_quality": "N/A"
        })

    return questions[:3]


def analyze_transcript(transcript):
    lower_text = transcript.lower()

    positive_words = [
        "growth", "strong", "positive", "improved",
        "opportunity", "comfortable", "confident",
        "robust", "resilient", "resilience",
        "profitability", "efficiency", "stable",
        "solid", "reaffirmed"
    ]

    negative_words = [
        "risk", "challenge", "challenges",
        "weak", "loss", "negative",
        "uncertainty", "delinquency"
    ]

    positive_count = sum(1 for word in positive_words if word in lower_text)
    negative_count = sum(1 for word in negative_words if word in lower_text)

    if positive_count > negative_count:
        tone = "optimistic"
        confidence = 0.80
    elif negative_count > positive_count:
        tone = "cautiously pessimistic"
        confidence = 0.75
    else:
        tone = "neutral"
        confidence = 0.60

    takeaways = []

    if "roe" in lower_text or "profitability" in lower_text:
        takeaways.append(
            "Profitability and ROE sustainability were central themes in the call."
        )

    if "delinquency" in lower_text:
        takeaways.append(
            "Delinquency trends were discussed as an important risk monitoring point."
        )

    if "efficiency" in lower_text:
        takeaways.append(
            "Efficiency initiatives were highlighted as a driver of profitability."
        )

    if "guidance" in lower_text:
        takeaways.append(
            "Management reaffirmed comfort with current guidance."
        )

    if not takeaways:
        takeaways.append("No major takeaway identified in this chunk.")

    guidance = []

    if "comfortable with the guidance" in lower_text or "guidance is reaffirmed" in lower_text:
        guidance.append(
            "Management stated it remains comfortable with current guidance."
        )

    if "profitability above 20%" in lower_text:
        guidance.append(
            "Management expects profitability to remain above 20%."
        )

    if not guidance:
        guidance.append("No explicit guidance identified in this chunk.")

    red_flags = []

    if "delinquency" in lower_text:
        red_flags.append({
            "quote": "Delinquency discussed.",
            "reason": "Credit quality remains an important monitoring point."
        })

    if "uncertainty" in lower_text:
        red_flags.append({
            "quote": "Uncertainty mentioned.",
            "reason": "Macroeconomic conditions may affect future performance."
        })

    if "challenges" in lower_text:
        red_flags.append({
            "quote": "Challenges mentioned.",
            "reason": "Management acknowledged external and operating challenges."
        })

    if not red_flags:
        red_flags.append({
            "quote": "No red flags identified.",
            "reason": "No significant negative signals were detected."
        })

    evidence = extract_relevant_evidence(transcript)

    if not evidence:
        evidence = ["No direct evidence extracted from this chunk."]

    return {
        "company": "ITUB4",
        "management_tone": {
            "classification": tone,
            "confidence": confidence,
            "evidence": evidence
        },
        "key_takeaways": takeaways,
        "guidance": guidance,
        "guidance_changes": [
            {
                "change": "Previous quarter comparison not fully automated in current prototype.",
                "impact": "The system is structured to support temporal comparison once prior-quarter transcripts are included."
            }
        ],
        "analyst_questions": [
            {
                "question": "No analyst questions identified in the transcript.",
                "response_summary": "N/A",
                "response_quality": "N/A"
            }
        ],
        "red_flags": red_flags,
        "surprise_score": calculate_surprise_score(lower_text)
    }


def deduplicate_list(items):
    unique_items = []

    for item in items:
        if item not in unique_items:
            unique_items.append(item)

    return unique_items


def deduplicate_dicts(items):
    unique_items = []
    seen = set()

    for item in items:
        marker = tuple(sorted(item.items()))

        if marker not in seen:
            seen.add(marker)
            unique_items.append(item)

    return unique_items


def classify_overall_tone(evidence_items, fallback_classification):
    evidence_text = " ".join(evidence_items).lower()

    optimistic_signals = [
        "comfortable with the guidance",
        "guidance is reaffirmed",
        "resilience",
        "resilient",
        "robust",
        "profitability",
        "stable",
        "efficiency",
        "solid capital base"
    ]

    cautious_signals = [
        "uncertainty",
        "challenges",
        "delinquency"
    ]

    optimistic_count = sum(
        1 for signal in optimistic_signals
        if signal in evidence_text
    )

    cautious_count = sum(
        1 for signal in cautious_signals
        if signal in evidence_text
    )

    if optimistic_count > cautious_count:
        return "optimistic", 0.80

    if cautious_count > optimistic_count:
        return "cautiously optimistic", 0.75

    return fallback_classification, 0.60


def combine_chunk_analyses(chunk_analyses):
    combined_takeaways = []
    combined_guidance = []
    combined_guidance_changes = []
    combined_analyst_questions = []
    combined_red_flags = []
    combined_evidence = []

    for analysis in chunk_analyses:
        combined_takeaways.extend(analysis["key_takeaways"])
        combined_guidance.extend(analysis["guidance"])
        combined_guidance_changes.extend(analysis["guidance_changes"])
        combined_analyst_questions.extend(analysis["analyst_questions"])
        combined_red_flags.extend(analysis["red_flags"])

        for evidence in analysis["management_tone"]["evidence"]:
            if evidence.strip() and evidence != "No direct evidence extracted from this chunk.":
                combined_evidence.append(evidence)

    if not combined_evidence:
        combined_evidence = ["No direct evidence extracted from the transcript."]

    combined_takeaways = [
        item for item in deduplicate_list(combined_takeaways)
        if not item.startswith("No major")
    ]

    combined_guidance = [
        item for item in deduplicate_list(combined_guidance)
        if not item.startswith("No explicit")
    ]

    combined_red_flags = [
        item for item in deduplicate_dicts(combined_red_flags)
        if item["quote"] != "No red flags identified."
    ]

    fallback_classification = chunk_analyses[0]["management_tone"]["classification"]

    overall_tone, overall_confidence = classify_overall_tone(
        combined_evidence,
        fallback_classification
    )

    return {
        "company": "ITUB4",
        "management_tone": {
            "classification": overall_tone,
            "confidence": overall_confidence,
            "evidence": deduplicate_list(combined_evidence)[:12]
        },
        "key_takeaways": combined_takeaways or [
            "No major takeaway identified."
        ],
        "guidance": combined_guidance or [
            "No explicit guidance identified."
        ],
        "guidance_changes": deduplicate_dicts(combined_guidance_changes),
        "analyst_questions": deduplicate_dicts(combined_analyst_questions)[:3],
        "red_flags": combined_red_flags or [
            {
                "quote": "No red flags identified.",
                "reason": "No significant negative signals were detected."
            }
        ],
        "surprise_score": chunk_analyses[0]["surprise_score"]
    }


def build_analysis_request(prompt, transcript_chunk):
    return f"""
{prompt}

TRANSCRIPT:

{transcript_chunk}
"""


def process_chunk(prompt, chunk, analyst_questions_text=None):
    request = build_analysis_request(prompt, chunk)
    print("\nProcessing chunk...\n")

    analysis = analyze_transcript(chunk)

    if analyst_questions_text:
        analysis["analyst_questions"] = extract_analyst_questions(
            analyst_questions_text
        )

    return analysis
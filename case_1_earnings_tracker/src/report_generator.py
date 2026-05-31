def generate_report(analysis):
    tone = analysis["management_tone"]["classification"]
    confidence = analysis["management_tone"]["confidence"]

    evidence = "\n".join(
        f"> {item}"
        for item in analysis["management_tone"]["evidence"]
    )

    takeaways = "\n".join(
        f"- {item}" for item in analysis["key_takeaways"]
    )

    guidance = "\n".join(
        f"- {item}" for item in analysis["guidance"]
    )

    guidance_changes = "\n".join(
        f"- {item['change']} ({item['impact']})"
        for item in analysis["guidance_changes"]
    )

    analyst_questions = "\n\n".join(
        f"""### Question
{item['question']}

**Response Summary:** {item['response_summary']}

**Response Quality:** {item['response_quality']}"""
        for item in analysis["analyst_questions"]
    )

    red_flags = "\n".join(
        f"- {item['quote']} ({item['reason']})"
        for item in analysis["red_flags"]
    )

    report = f"""
# Earnings Call Intelligence Report

## Management Tone
Classification: **{tone}**

Confidence: **{confidence}**

Evidence:
{evidence}

## Key Takeaways
{takeaways}

## Guidance
{guidance}

## Guidance Changes
{guidance_changes}

## Analyst Questions
{analyst_questions}

## Red Flags
{red_flags}

## Surprise Score
Score: **{analysis["surprise_score"]["score"]}/10**

{analysis["surprise_score"]["justification"]}
"""

    return report
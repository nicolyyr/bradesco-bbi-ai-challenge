def generate_report(analysis):
    tone = analysis["management_tone"]["classification"]
    confidence = analysis["management_tone"]["confidence"]
    evidence = analysis["management_tone"]["evidence"][0]

    takeaways = "\n".join(
        f"- {item}" for item in analysis["key_takeaways"]
    )

    guidance = "\n".join(
        f"- {item}" for item in analysis["guidance"]
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
> {evidence}

## Key Takeaways
{takeaways}

## Guidance
{guidance}

## Red Flags
{red_flags}

## Surprise Score
Score: **{analysis["surprise_score"]["score"]}/10**

{analysis["surprise_score"]["justification"]}
"""

    return report
def generate_report(analysis):
    tone = analysis["management_tone"]["classification"]
    evidence = analysis["management_tone"]["evidence"][0]

    takeaways = "\n".join(
        f"- {item}" for item in analysis["key_takeaways"]
    )

    report = f"""
# Earnings Call Intelligence Report

## Management Tone
The overall management tone was **{tone}**.

Evidence:
> {evidence}

## Key Takeaways
{takeaways}
"""

    return report
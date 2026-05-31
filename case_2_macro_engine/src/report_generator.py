def generate_report(analysis):
    positive_sectors = "\n".join(
        f"- {item['sector']}: {item['rationale']}"
        for item in analysis["positive_sectors"]
    )

    negative_sectors = "\n".join(
        f"- {item['sector']}: {item['rationale']}"
        for item in analysis["negative_sectors"]
    )

    positive_tickers = "\n".join(
        f"- {item['ticker']}: {item['rationale']}"
        for item in analysis["positive_tickers"]
    )

    negative_tickers = "\n".join(
        f"- {item['ticker']}: {item['rationale']}"
        for item in analysis["negative_tickers"]
    )

    risks = "\n".join(
        f"- {risk}"
        for risk in analysis["market_risks"]
    )

    report = f"""
# Macro Scenario Analysis Report

## Scenario Summary

{analysis["scenario_summary"]}

## Top Benefited Sectors

{positive_sectors}

## Top Negatively Impacted Sectors

{negative_sectors}

## Positive Exposure Tickers

{positive_tickers}

## Negative Exposure Tickers

{negative_tickers}

## Main Risks

{risks}

## Investment View

{analysis["investment_view"]}
"""

    return report
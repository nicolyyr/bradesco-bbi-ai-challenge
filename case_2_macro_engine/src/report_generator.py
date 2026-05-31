def generate_report(analysis):
    positive_sectors = "\n".join(
        f"- {sector}" for sector in analysis["positive_sectors"]
    )

    negative_sectors = "\n".join(
        f"- {sector}" for sector in analysis["negative_sectors"]
    )

    positive_tickers = "\n".join(
        f"- {ticker}" for ticker in analysis["positive_tickers"]
    )

    negative_tickers = "\n".join(
        f"- {ticker}" for ticker in analysis["negative_tickers"]
    )

    risks = "\n".join(
        f"- {risk}" for risk in analysis["market_risks"]
    )

    report = f"""
# Macro Scenario Analysis Report

## Scenario Summary

{analysis["scenario_summary"]}

## Positive Sectors

{positive_sectors}

## Negative Sectors

{negative_sectors}

## Positive Tickers

{positive_tickers}

## Negative Tickers

{negative_tickers}

## Market Risks

{risks}

## Investment View

{analysis["investment_view"]}
"""

    return report
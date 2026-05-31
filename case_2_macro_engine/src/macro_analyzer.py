from sector_mapper import map_sectors


def analyze_macro_scenario(scenario_text):
    sectors = map_sectors(scenario_text)

    return {
        "scenario_summary": (
            "Higher interest rates, persistent inflation and weaker economic growth."
        ),
        "positive_sectors": sectors["positive_sectors"],
        "negative_sectors": sectors["negative_sectors"],
        "market_risks": [
            "Slower economic activity",
            "Reduced consumer spending",
            "Higher borrowing costs"
        ],
        "investment_view": (
            "Defensive positioning with preference for financial institutions."
        )
    }
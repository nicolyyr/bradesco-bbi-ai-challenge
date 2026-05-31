def map_sectors(scenario_text):
    scenario_lower = scenario_text.lower()

    positive_sectors = []
    negative_sectors = []

    if "interest rates" in scenario_lower:
        positive_sectors.append("Banks")
        negative_sectors.append("Construction")
        negative_sectors.append("Retail")

    if "inflation" in scenario_lower:
        negative_sectors.append("Consumer Goods")

    if "consumer spending" in scenario_lower:
        negative_sectors.append("Consumer Discretionary")

    return {
        "positive_sectors": list(set(positive_sectors)),
        "negative_sectors": list(set(negative_sectors))
    }
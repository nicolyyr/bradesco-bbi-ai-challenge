SECTOR_TICKERS = {
    "Banks": {
        "positive": ["ITUB4", "BBAS3", "BBDC4"],
        "negative": []
    },
    "Construction": {
        "positive": [],
        "negative": ["MRVE3", "CYRE3", "EZTC3"]
    },
    "Retail": {
        "positive": [],
        "negative": ["MGLU3", "LREN3", "AMER3"]
    },
    "Consumer Goods": {
        "positive": [],
        "negative": ["NTCO3", "ASAI3", "PCAR3"]
    },
    "Consumer Discretionary": {
        "positive": [],
        "negative": ["CVCB3", "SOMA3", "ARZZ3"]
    }
}


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

    positive_sectors = list(set(positive_sectors))
    negative_sectors = list(set(negative_sectors))

    positive_tickers = []
    negative_tickers = []

    for sector in positive_sectors:
        positive_tickers.extend(SECTOR_TICKERS[sector]["positive"])

    for sector in negative_sectors:
        negative_tickers.extend(SECTOR_TICKERS[sector]["negative"])

    return {
        "positive_sectors": positive_sectors,
        "negative_sectors": negative_sectors,
        "positive_tickers": positive_tickers[:3],
        "negative_tickers": negative_tickers[:3]
    }
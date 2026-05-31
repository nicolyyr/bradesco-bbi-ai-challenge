SECTOR_TICKERS = {
    "Banks": {
        "positive": [
            {
                "ticker": "ITUB4",
                "rationale": "Large incumbent bank with strong balance sheet and ability to benefit from higher interest income."
            },
            {
                "ticker": "BBAS3",
                "rationale": "Credit-focused bank that may benefit from higher rates, although asset quality must be monitored."
            },
            {
                "ticker": "BBDC4",
                "rationale": "Major private bank with exposure to credit spreads and financial intermediation."
            }
        ],
        "negative": []
    },

    "Insurance": {
        "positive": [
            {
                "ticker": "BBSE3",
                "rationale": "Higher interest rates may support financial income from reserves."
            }
        ],
        "negative": []
    },

    "Utilities": {
        "positive": [
            {
                "ticker": "TAEE11",
                "rationale": "Defensive and regulated cash flows may become attractive in risk-off scenarios."
            }
        ],
        "negative": []
    },

    "Oil & Gas": {
        "positive": [
            {
                "ticker": "PETR4",
                "rationale": "Large cash-generative oil producer with resilience in uncertain macro environments."
            }
        ],
        "negative": []
    },

    "Pulp & Paper": {
        "positive": [
            {
                "ticker": "SUZB3",
                "rationale": "Export-oriented company that may benefit from weaker domestic growth and FX effects."
            }
        ],
        "negative": []
    },

    "Construction": {
        "positive": [],
        "negative": [
            {
                "ticker": "MRVE3",
                "rationale": "Higher interest rates pressure mortgage affordability and housing demand."
            },
            {
                "ticker": "CYRE3",
                "rationale": "Real estate developers are sensitive to financing costs and weaker demand."
            }
        ]
    },

    "Retail": {
        "positive": [],
        "negative": [
            {
                "ticker": "MGLU3",
                "rationale": "Consumer discretionary retailers are pressured by tighter credit and weaker spending."
            },
            {
                "ticker": "LREN3",
                "rationale": "Apparel retail is exposed to slowing consumption and household income pressure."
            }
        ]
    },

    "Consumer Goods": {
        "positive": [],
        "negative": [
            {
                "ticker": "NTCO3",
                "rationale": "Inflation can pressure margins and reduce consumer purchasing power."
            }
        ]
    },

    "Consumer Discretionary": {
        "positive": [],
        "negative": [
            {
                "ticker": "CVCB3",
                "rationale": "Travel and discretionary consumption tend to suffer when spending slows."
            }
        ]
    },

    "Capital Goods": {
        "positive": [],
        "negative": [
            {
                "ticker": "WEGE3",
                "rationale": "Lower growth expectations may reduce investment appetite."
            }
        ]
    }
}


def map_sectors(scenario_text):
    scenario_lower = scenario_text.lower()

    positive_sectors = []
    negative_sectors = []

    rate_hike = any(
        cue in scenario_lower
        for cue in ("interest rate", "raised rates", "rate hike", "tightening", "hiked")
    ) or ("rates" in scenario_lower and "raised" in scenario_lower)
    rate_cut = any(
        cue in scenario_lower
        for cue in ("rate cut", "cut rates", "lower interest", "easing", "loosening")
    )

    if rate_hike:
        positive_sectors.extend([
            {
                "sector": "Banks",
                "rationale": "Higher interest rates may support net interest income and credit spreads for large banks."
            },
            {
                "sector": "Insurance",
                "rationale": "Insurers can benefit from higher yields on financial reserves and investment portfolios."
            },
            {
                "sector": "Utilities",
                "rationale": "Defensive sectors may attract investors during periods of weaker growth and higher uncertainty."
            },
            {
                "sector": "Oil & Gas",
                "rationale": "Companies with strong cash generation may be relatively resilient in risk-off environments."
            },
            {
                "sector": "Pulp & Paper",
                "rationale": "Export-oriented companies may benefit from currency depreciation associated with weaker domestic growth."
            }
        ])

        negative_sectors.extend([
            {
                "sector": "Construction",
                "rationale": "Higher interest rates increase financing costs and reduce housing affordability."
            },
            {
                "sector": "Retail",
                "rationale": "Retailers are pressured by tighter credit conditions and weaker consumer demand."
            }
        ])

    if "inflation" in scenario_lower:
        negative_sectors.append({
            "sector": "Consumer Goods",
            "rationale": "Persistent inflation can pressure margins and reduce household purchasing power."
        })

    if "consumer spending" in scenario_lower:
        negative_sectors.append({
            "sector": "Consumer Discretionary",
            "rationale": "Slower consumer spending directly affects discretionary purchases and services."
        })

    if "growth expectations" in scenario_lower or "economic growth" in scenario_lower:
        negative_sectors.append({
            "sector": "Capital Goods",
            "rationale": "Lower growth expectations may reduce corporate investment and demand for capital equipment."
        })

    if rate_cut:
        positive_sectors.extend([
            {
                "sector": "Construction",
                "rationale": "Lower rates improve mortgage affordability and housing demand, supporting developers."
            },
            {
                "sector": "Retail",
                "rationale": "Easier credit and cheaper financing tend to lift consumer demand and discretionary spending."
            },
            {
                "sector": "Capital Goods",
                "rationale": "Lower financing costs can revive corporate investment and equipment demand."
            },
        ])
        negative_sectors.append({
            "sector": "Banks",
            "rationale": "Lower rates can compress net interest margins for large lenders."
        })

    # Robust fallback: if no macro cue was recognized, return a defensive-vs-cyclical
    # split so the baseline never emits an empty result (audit fix).
    if not positive_sectors and not negative_sectors:
        positive_sectors.extend([
            {"sector": "Utilities", "rationale": "Regulated, defensive cash flows are resilient when the macro signal is unclear."},
            {"sector": "Oil & Gas", "rationale": "Cash-generative exporters offer ballast under uncertain conditions."},
        ])
        negative_sectors.extend([
            {"sector": "Retail", "rationale": "Discretionary consumption is most exposed to an ambiguous demand outlook."},
        ])

    positive_sectors = _dedupe_sectors(positive_sectors)
    negative_sectors = _dedupe_sectors(negative_sectors)

    positive_tickers = []
    negative_tickers = []

    for sector_info in positive_sectors:
        sector = sector_info["sector"]
        positive_tickers.extend(
            SECTOR_TICKERS.get(sector, {}).get("positive", [])
        )

    for sector_info in negative_sectors:
        sector = sector_info["sector"]
        negative_tickers.extend(
            SECTOR_TICKERS.get(sector, {}).get("negative", [])
        )

    return {
        "positive_sectors": positive_sectors[:5],
        "negative_sectors": negative_sectors[:5],
        "positive_tickers": positive_tickers[:3],
        "negative_tickers": negative_tickers[:3]
    }


def _dedupe_sectors(sectors):
    """Keep the first rationale seen for each sector name, preserving order."""
    seen = set()
    out = []
    for item in sectors:
        name = item["sector"]
        if name not in seen:
            seen.add(name)
            out.append(item)
    return out
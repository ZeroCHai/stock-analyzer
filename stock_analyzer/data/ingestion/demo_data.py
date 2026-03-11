"""
Demo-mode sample data — realistic values for UI testing without network access.
Modelled on approximate 2024 figures; not for investment decisions.
"""

DEMO_STOCKS: dict[str, dict] = {
    "AAPL": {
        "symbol": "AAPL", "longName": "Apple Inc.",
        "sector": "Technology", "industry": "Consumer Electronics",
        "country": "United States",
        "longBusinessSummary": (
            "Apple Inc. designs, manufactures, and markets smartphones, personal "
            "computers, tablets, wearables, and accessories worldwide. It sells "
            "through its retail and online stores, and through third-party cellular "
            "network carriers, wholesalers, retailers, and resellers."
        ),
        "currentPrice": 189.30, "marketCap": 2.93e12,
        "trailingPE": 30.8, "forwardPE": 27.4, "priceToBook": 46.2,
        "priceToSalesTrailing12Months": 7.8, "enterpriseToEbitda": 23.1, "pegRatio": 2.9,
        "grossMargins": 0.454, "operatingMargins": 0.302, "profitMargins": 0.254,
        "returnOnEquity": 1.471, "returnOnAssets": 0.222,
        "revenueGrowth": 0.051, "earningsGrowth": 0.112,
        "currentRatio": 0.99, "debtToEquity": 181.0,
        "freeCashflow": 99.6e9,
        "dividendYield": 0.0052, "payoutRatio": 0.157,
        "trailingEps": 6.13, "forwardEps": 6.90, "bookValue": 4.10,
        "beta": 1.24, "fiftyTwoWeekHigh": 199.62, "fiftyTwoWeekLow": 164.08,
    },
    "MSFT": {
        "symbol": "MSFT", "longName": "Microsoft Corporation",
        "sector": "Technology", "industry": "Software—Infrastructure",
        "country": "United States",
        "longBusinessSummary": (
            "Microsoft Corporation develops, licenses, and supports software, services, "
            "devices, and solutions worldwide. Its segments include Productivity and "
            "Business Processes, Intelligent Cloud, and More Personal Computing."
        ),
        "currentPrice": 415.50, "marketCap": 3.08e12,
        "trailingPE": 36.2, "forwardPE": 30.1, "priceToBook": 12.5,
        "priceToSalesTrailing12Months": 13.0, "enterpriseToEbitda": 26.4, "pegRatio": 2.1,
        "grossMargins": 0.699, "operatingMargins": 0.447, "profitMargins": 0.358,
        "returnOnEquity": 0.381, "returnOnAssets": 0.188,
        "revenueGrowth": 0.160, "earningsGrowth": 0.212,
        "currentRatio": 1.27, "debtToEquity": 36.8,
        "freeCashflow": 74.1e9,
        "dividendYield": 0.0070, "payoutRatio": 0.252,
        "trailingEps": 11.45, "forwardEps": 13.80, "bookValue": 33.20,
        "beta": 0.90, "fiftyTwoWeekHigh": 468.35, "fiftyTwoWeekLow": 362.90,
    },
    "NVDA": {
        "symbol": "NVDA", "longName": "NVIDIA Corporation",
        "sector": "Technology", "industry": "Semiconductors",
        "country": "United States",
        "longBusinessSummary": (
            "NVIDIA Corporation provides graphics, and compute and networking solutions "
            "in the United States, Taiwan, China, and internationally. The company "
            "operates in two segments, Graphics and Compute & Networking."
        ),
        "currentPrice": 875.40, "marketCap": 2.16e12,
        "trailingPE": 68.5, "forwardPE": 35.2, "priceToBook": 38.1,
        "priceToSalesTrailing12Months": 22.0, "enterpriseToEbitda": 45.6, "pegRatio": 0.9,
        "grossMargins": 0.723, "operatingMargins": 0.618, "profitMargins": 0.557,
        "returnOnEquity": 1.232, "returnOnAssets": 0.558,
        "revenueGrowth": 1.220, "earningsGrowth": 2.686,
        "currentRatio": 4.17, "debtToEquity": 42.1,
        "freeCashflow": 27.0e9,
        "dividendYield": 0.0003, "payoutRatio": 0.016,
        "trailingEps": 12.79, "forwardEps": 24.87, "bookValue": 22.97,
        "beta": 1.67, "fiftyTwoWeekHigh": 974.00, "fiftyTwoWeekLow": 373.87,
    },
    "GOOGL": {
        "symbol": "GOOGL", "longName": "Alphabet Inc.",
        "sector": "Communication Services", "industry": "Internet Content & Information",
        "country": "United States",
        "longBusinessSummary": (
            "Alphabet Inc. provides various products and platforms in the United States, "
            "Europe, the Middle East, Africa, the Asia-Pacific, Canada, and Latin America. "
            "It operates through Google Services, Google Cloud, and Other Bets segments."
        ),
        "currentPrice": 172.63, "marketCap": 2.16e12,
        "trailingPE": 23.8, "forwardPE": 20.5, "priceToBook": 6.5,
        "priceToSalesTrailing12Months": 6.4, "enterpriseToEbitda": 16.2, "pegRatio": 1.2,
        "grossMargins": 0.563, "operatingMargins": 0.316, "profitMargins": 0.240,
        "returnOnEquity": 0.315, "returnOnAssets": 0.167,
        "revenueGrowth": 0.152, "earningsGrowth": 0.310,
        "currentRatio": 2.10, "debtToEquity": 10.1,
        "freeCashflow": 60.8e9,
        "dividendYield": None, "payoutRatio": None,
        "trailingEps": 7.26, "forwardEps": 8.44, "bookValue": 26.70,
        "beta": 1.04, "fiftyTwoWeekHigh": 193.31, "fiftyTwoWeekLow": 130.67,
    },
    "JPM": {
        "symbol": "JPM", "longName": "JPMorgan Chase & Co.",
        "sector": "Financial Services", "industry": "Banks—Diversified",
        "country": "United States",
        "longBusinessSummary": (
            "JPMorgan Chase & Co. operates as a financial services company worldwide. "
            "It operates through Consumer & Community Banking, Commercial Banking, "
            "Corporate & Investment Bank, and Asset & Wealth Management segments."
        ),
        "currentPrice": 198.47, "marketCap": 571e9,
        "trailingPE": 11.4, "forwardPE": 11.9, "priceToBook": 1.72,
        "priceToSalesTrailing12Months": 3.3, "enterpriseToEbitda": None, "pegRatio": 1.8,
        "grossMargins": 0.582, "operatingMargins": 0.395, "profitMargins": 0.295,
        "returnOnEquity": 0.162, "returnOnAssets": 0.012,
        "revenueGrowth": 0.218, "earningsGrowth": 0.355,
        "currentRatio": None, "debtToEquity": 128.0,
        "freeCashflow": None,
        "dividendYield": 0.0224, "payoutRatio": 0.255,
        "trailingEps": 17.42, "forwardEps": 16.65, "bookValue": 115.50,
        "beta": 1.12, "fiftyTwoWeekHigh": 220.82, "fiftyTwoWeekLow": 135.19,
    },
}

# ── Demo news (flat normalized schema, realistic ~March 2026) ─────────────────
# Timestamps: Mar 10=1773100800, Mar 8=1772928000, Mar 6=1772755200,
#             Mar 4=1772582400, Mar 2=1772409600, Feb 28=1772236800
DEMO_NEWS: dict[str, list[dict]] = {
    "AAPL": [
        {"title": "Apple Reports Q1 2026 Record Services Revenue of $28.9B",
         "link": "", "publisher": "Bloomberg", "providerPublishTime": 1773100800,
         "relatedTickers": ["AAPL"]},
        {"title": "Apple Intelligence Rolls Out Real-Time Translation for 40 Languages",
         "link": "", "publisher": "Reuters", "providerPublishTime": 1772928000,
         "relatedTickers": ["AAPL"]},
        {"title": "iPhone 17 Pre-Orders Surpass 50 Million in Opening Weekend",
         "link": "", "publisher": "CNBC", "providerPublishTime": 1772755200,
         "relatedTickers": ["AAPL"]},
        {"title": "Apple Expands India Manufacturing to Reduce China Dependency",
         "link": "", "publisher": "Financial Times", "providerPublishTime": 1772582400,
         "relatedTickers": ["AAPL"]},
        {"title": "Apple Vision Pro 2 Launch Slated for Q3 2026, New Leaks Suggest",
         "link": "", "publisher": "MacRumors", "providerPublishTime": 1772409600,
         "relatedTickers": ["AAPL"]},
    ],
    "MSFT": [
        {"title": "Microsoft Azure AI Revenue Grows 48% YoY, Beats Wall Street Estimates",
         "link": "", "publisher": "Bloomberg", "providerPublishTime": 1773100800,
         "relatedTickers": ["MSFT"]},
        {"title": "Microsoft Copilot Reaches 100 Million Enterprise Users Milestone",
         "link": "", "publisher": "Reuters", "providerPublishTime": 1772928000,
         "relatedTickers": ["MSFT"]},
        {"title": "Microsoft Acquires AI Startup Synthia for $4.2 Billion",
         "link": "", "publisher": "Wall Street Journal", "providerPublishTime": 1772755200,
         "relatedTickers": ["MSFT"]},
        {"title": "Microsoft Cloud Gross Margin Expands to 73% on Efficiency Gains",
         "link": "", "publisher": "CNBC", "providerPublishTime": 1772582400,
         "relatedTickers": ["MSFT"]},
        {"title": "Xbox Game Pass Surpasses 45 Million Subscribers Globally",
         "link": "", "publisher": "The Verge", "providerPublishTime": 1772409600,
         "relatedTickers": ["MSFT"]},
    ],
    "NVDA": [
        {"title": "NVIDIA Blackwell Ultra Ships 2 Million Units in Q4, Revenue Hits $43B",
         "link": "", "publisher": "Bloomberg", "providerPublishTime": 1773100800,
         "relatedTickers": ["NVDA"]},
        {"title": "NVIDIA Announces Next-Gen Rubin GPU Architecture for 2027",
         "link": "", "publisher": "Reuters", "providerPublishTime": 1772928000,
         "relatedTickers": ["NVDA"]},
        {"title": "NVIDIA Partners with Saudi Aramco for $10B AI Infrastructure Deal",
         "link": "", "publisher": "Financial Times", "providerPublishTime": 1772755200,
         "relatedTickers": ["NVDA"]},
        {"title": "NVIDIA Data Center Segment Now Accounts for 84% of Total Revenue",
         "link": "", "publisher": "CNBC", "providerPublishTime": 1772582400,
         "relatedTickers": ["NVDA"]},
        {"title": "NVIDIA Stock Hits New All-Time High Amid Continued AI Boom",
         "link": "", "publisher": "MarketWatch", "providerPublishTime": 1772236800,
         "relatedTickers": ["NVDA"]},
    ],
    "GOOGL": [
        {"title": "Alphabet Reports $105B Revenue in Q4 2025, Search Ad Growth Accelerates",
         "link": "", "publisher": "Bloomberg", "providerPublishTime": 1773100800,
         "relatedTickers": ["GOOGL"]},
        {"title": "Google Cloud Captures 24% Market Share, Closing Gap with Azure",
         "link": "", "publisher": "Reuters", "providerPublishTime": 1772928000,
         "relatedTickers": ["GOOGL"]},
        {"title": "Waymo Expands Robotaxi to 15 New US Cities in 2026 Rollout",
         "link": "", "publisher": "CNBC", "providerPublishTime": 1772755200,
         "relatedTickers": ["GOOGL"]},
        {"title": "Alphabet Announces $80B Share Buyback Programme",
         "link": "", "publisher": "Wall Street Journal", "providerPublishTime": 1772582400,
         "relatedTickers": ["GOOGL"]},
        {"title": "Gemini Ultra Beats GPT-5 on Key Reasoning Benchmarks, Google Claims",
         "link": "", "publisher": "The Information", "providerPublishTime": 1772236800,
         "relatedTickers": ["GOOGL"]},
    ],
    "JPM": [
        {"title": "JPMorgan Reports Record Full-Year 2025 Profit of $62B",
         "link": "", "publisher": "Bloomberg", "providerPublishTime": 1773100800,
         "relatedTickers": ["JPM"]},
        {"title": "JPMorgan Raises Dividend 12% as Capital Ratios Remain Robust",
         "link": "", "publisher": "Reuters", "providerPublishTime": 1772928000,
         "relatedTickers": ["JPM"]},
        {"title": "JPMorgan Investment Banking Fees Surge 38% on M&A Revival",
         "link": "", "publisher": "Financial Times", "providerPublishTime": 1772755200,
         "relatedTickers": ["JPM"]},
        {"title": "Fed Holds Rates Steady; Dimon Warns of Persistent Inflation Risk",
         "link": "", "publisher": "CNBC", "providerPublishTime": 1772582400,
         "relatedTickers": ["JPM", "BAC", "WFC"]},
        {"title": "JPMorgan AI Platform Reduces Back-Office Costs by $1.5B Annually",
         "link": "", "publisher": "Wall Street Journal", "providerPublishTime": 1772236800,
         "relatedTickers": ["JPM"]},
    ],
}


# Price history (daily Close, last 12 months simulated)
import pandas as pd
import numpy as np


def get_demo_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Return a plausible price history DataFrame for demo mode."""
    rng = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504, "5y": 1260}
    n = rng.get(period, 252)

    info = DEMO_STOCKS.get(symbol.upper(), {})
    price = info.get("currentPrice", 100.0)
    low52 = info.get("fiftyTwoWeekLow", price * 0.8)

    np.random.seed(abs(hash(symbol)) % (2**31))
    drift = (price / low52) ** (1 / 252) - 1
    vol   = 0.015
    returns = np.random.normal(drift, vol, n)
    prices  = price * np.exp(-np.cumsum(returns[::-1]))[::-1]

    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
    return pd.DataFrame({"Close": prices, "Open": prices * 0.999,
                         "High": prices * 1.005, "Low": prices * 0.995,
                         "Volume": np.random.randint(20e6, 80e6, n)},
                        index=dates)

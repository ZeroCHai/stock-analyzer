"""Fetch US stock data from Yahoo Finance and persist to SQLite.

Falls back to demo data automatically when the network is unavailable.
Set DEMO_MODE=true in environment (or .env) to force demo mode.
"""

import os
import yfinance as yf
import pandas as pd
from stock_analyzer.data.db import upsert_stock, upsert_financials, get_financials
from stock_analyzer.data.ingestion.demo_data import DEMO_STOCKS, DEMO_NEWS, get_demo_history

# Force demo mode via env var, or auto-detect on network failure
_DEMO_MODE: bool | None = None


def is_demo_mode() -> bool:
    global _DEMO_MODE
    if _DEMO_MODE is None:
        _DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
    return _DEMO_MODE


def set_demo_mode(enabled: bool):
    global _DEMO_MODE
    _DEMO_MODE = enabled


def fetch_stock(symbol: str, force: bool = False) -> dict:
    """
    Return the .info dict for a symbol.
    Uses SQLite cache unless force=True.
    Falls back to demo data on network error.
    """
    symbol = symbol.upper()

    if not force:
        cached = get_financials(symbol)
        if cached:
            return cached

    if is_demo_mode():
        return _demo_stock(symbol)

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or info.get("quoteType") is None:
            raise ValueError(f"Symbol '{symbol}' not found on Yahoo Finance.")
        upsert_stock(
            symbol=symbol,
            name=info.get("longName", symbol),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            country=info.get("country", ""),
        )
        upsert_financials(symbol, info)
        return info
    except Exception as e:
        # Auto-fallback to demo if network blocked
        if symbol in DEMO_STOCKS:
            set_demo_mode(True)
            return _demo_stock(symbol)
        raise


def _demo_stock(symbol: str) -> dict:
    if symbol not in DEMO_STOCKS:
        available = ", ".join(sorted(DEMO_STOCKS))
        raise ValueError(
            f"'{symbol}' not in demo data. Available demo symbols: {available}"
        )
    return DEMO_STOCKS[symbol]


def fetch_price_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Return OHLCV history as a DataFrame."""
    if is_demo_mode():
        return get_demo_history(symbol, period)
    try:
        return yf.Ticker(symbol.upper()).history(period=period)
    except Exception:
        return get_demo_history(symbol, period)


def fetch_income_statement(symbol: str) -> pd.DataFrame:
    if is_demo_mode():
        return pd.DataFrame()
    return yf.Ticker(symbol.upper()).financials


def fetch_balance_sheet(symbol: str) -> pd.DataFrame:
    if is_demo_mode():
        return pd.DataFrame()
    return yf.Ticker(symbol.upper()).balance_sheet


def fetch_cash_flow(symbol: str) -> pd.DataFrame:
    if is_demo_mode():
        return pd.DataFrame()
    return yf.Ticker(symbol.upper()).cashflow


# ── News ───────────────────────────────────────────────────────────────────────

# SPDR sector ETFs used as proxies for industry-level news
SECTOR_ETF: dict[str, str] = {
    "Technology":             "XLK",
    "Healthcare":             "XLV",
    "Financials":             "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples":       "XLP",
    "Energy":                 "XLE",
    "Utilities":              "XLU",
    "Basic Materials":        "XLB",
    "Industrials":            "XLI",
    "Real Estate":            "XLRE",
    "Communication Services": "XLC",
}

# Top large-cap peers per sector for targeted competitive-intelligence news
SECTOR_PEERS: dict[str, list[str]] = {
    "Technology":             ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD", "INTC", "ORCL"],
    "Healthcare":             ["JNJ", "UNH", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY"],
    "Financials":             ["JPM", "BAC", "WFC", "GS", "MS", "BRK-B", "C", "BLK", "AXP", "USB"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TJX", "LOW", "BKNG", "TGT"],
    "Consumer Staples":       ["WMT", "PG", "KO", "PEP", "COST", "PM", "MO", "CL", "MDLZ", "EL"],
    "Energy":                 ["XOM", "CVX", "COP", "EOG", "SLB", "OXY", "MPC", "PSX", "VLO", "HES"],
    "Utilities":              ["NEE", "DUK", "SO", "D", "EXC", "AEP", "XEL", "SRE", "WEC", "ED"],
    "Basic Materials":        ["LIN", "APD", "SHW", "ECL", "NEM", "FCX", "DOW", "PPG", "NUE", "VMC"],
    "Industrials":            ["GE", "HON", "CAT", "UPS", "DE", "LMT", "RTX", "BA", "MMM", "FDX"],
    "Real Estate":            ["AMT", "PLD", "EQIX", "CCI", "PSA", "O", "DLR", "WELL", "SPG", "AVB"],
    "Communication Services": ["META", "GOOGL", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA"],
}


def _normalize_news_item(item: dict) -> dict:
    """
    Normalize a Yahoo Finance news item to a consistent schema.

    yfinance ≥0.2.38 wraps everything under a 'content' key with different
    field names. This function returns the old flat schema so all downstream
    code (UI renderer + AI prompts) works unchanged.
    """
    content = item.get("content")
    if content:
        # New format (yfinance 1.x)
        pub_date = content.get("pubDate", "")
        try:
            from datetime import datetime
            ts = int(datetime.fromisoformat(
                pub_date.replace("Z", "+00:00")
            ).timestamp())
        except Exception:
            ts = 0
        click_url    = content.get("clickThroughUrl") or {}
        canonical    = content.get("canonicalUrl") or {}
        tickers = [
            t.get("symbol", "")
            for t in (content.get("finance") or {}).get("stockTickers", [])
            if t.get("symbol")
        ]
        return {
            "title":               content.get("title", ""),
            "link":                click_url.get("url", "") or canonical.get("url", ""),
            "publisher":           (content.get("provider") or {}).get("displayName", ""),
            "providerPublishTime": ts,
            "relatedTickers":      tickers,
        }
    # Old flat format — pass through as-is
    return item


def fetch_news(symbol: str, max_items: int = 15) -> list:
    """Return recent news for a symbol as a list of dicts from Yahoo Finance."""
    if is_demo_mode():
        return DEMO_NEWS.get(symbol.upper(), [])[:max_items]
    try:
        raw = yf.Ticker(symbol.upper()).news or []
        return [_normalize_news_item(item) for item in raw[:max_items]]
    except Exception:
        return []


def fetch_industry_news(sector: str, max_items: int = 15) -> list:
    """Return news for the SPDR sector ETF matching the given sector name."""
    etf = SECTOR_ETF.get(sector, "")
    if not etf:
        return []
    return fetch_news(etf, max_items)


def fetch_peers_news_by_list(
    tickers: list[str],
    max_per_ticker: int = 5,
    max_total: int = 20,
) -> tuple[list, list]:
    """
    Fetch and aggregate news for an explicit list of ticker symbols.

    Returns:
        (news_list, tickers_that_returned_news) sorted newest-first, deduplicated.
    """
    all_news: list = []
    queried: list = []

    for ticker in tickers:
        t = ticker.strip().upper()
        if not t:
            continue
        news = fetch_news(t, max_items=max_per_ticker)
        if news:
            all_news.extend(news)
            queried.append(t)

    all_news.sort(key=lambda x: x.get("providerPublishTime", 0), reverse=True)
    seen: set = set()
    deduped: list = []
    for item in all_news:
        title = item.get("title", "")
        if title and title not in seen:
            seen.add(title)
            deduped.append(item)

    return deduped[:max_total], queried


def fetch_sector_peers_news(
    sector: str,
    exclude_symbol: str = "",
    max_per_ticker: int = 5,
    max_total: int = 20,
) -> tuple[list, list]:
    """
    Auto-detect the top-5 large-cap peers for the sector and fetch their news.
    Delegates to fetch_peers_news_by_list().
    """
    candidates = [p for p in SECTOR_PEERS.get(sector, [])
                  if p.upper() != exclude_symbol.upper()]
    return fetch_peers_news_by_list(candidates[:5], max_per_ticker, max_total)


# ── Sector Markets ─────────────────────────────────────────────────────────────

# Maps SECTOR_ETF display names to yfinance Sector API keys
SECTOR_YF_KEY: dict[str, str] = {
    "Technology":             "technology",
    "Healthcare":             "healthcare",
    "Financials":             "financial-services",
    "Consumer Discretionary": "consumer-cyclical",
    "Consumer Staples":       "consumer-defensive",
    "Energy":                 "energy",
    "Utilities":              "utilities",
    "Basic Materials":        "basic-materials",
    "Industrials":            "industrials",
    "Real Estate":            "real-estate",
    "Communication Services": "communication-services",
}


def fetch_sector_performance() -> list[dict]:
    """
    Fetch 1-day, 1-week, and 1-month price performance for all 11 SPDR sector ETFs.
    Returns a list of dicts sorted by 1-day change (descending).
    """
    results = []
    for sector_name, etf_sym in SECTOR_ETF.items():
        try:
            hist = yf.Ticker(etf_sym).history(period="1mo")
            if hist.empty:
                continue
            price  = float(hist["Close"].iloc[-1])
            chg_1d = float(hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) if len(hist) >= 2  else None
            chg_1w = float(hist["Close"].iloc[-1] / hist["Close"].iloc[-6] - 1) if len(hist) >= 6  else None
            chg_1m = float(hist["Close"].iloc[-1] / hist["Close"].iloc[0]  - 1) if len(hist) >= 15 else None
            results.append({
                "Sector": sector_name,
                "ETF":    etf_sym,
                "Price":  price,
                "1D %":   chg_1d,
                "1W %":   chg_1w,
                "1M %":   chg_1m,
            })
        except Exception:
            pass
    results.sort(key=lambda x: (x.get("1D %") or -999), reverse=True)
    return results


def fetch_sector_details(sector_name: str) -> dict:
    """
    Fetch top companies and sub-industries for a sector via yf.Sector().
    Returns {"top_companies": DataFrame, "industries": DataFrame} or {} on failure.
    """
    key = SECTOR_YF_KEY.get(sector_name, "")
    if not key:
        return {}
    try:
        s = yf.Sector(key)
        return {
            "top_companies": getattr(s, "top_companies", pd.DataFrame()),
            "industries":    getattr(s, "industries",    pd.DataFrame()),
        }
    except Exception:
        return {}


# ── Prediction Markets ─────────────────────────────────────────────────────────

def fetch_prediction_markets() -> list[dict]:
    """
    Fetch prediction market quotes from Yahoo Finance.
    Returns a list of quote dicts on success, or an empty list on failure.
    """
    import requests

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/markets/prediction-markets/",
    }

    endpoints = [
        "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved",
        "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved",
    ]
    params = {
        "scrIds":  "predmarket_most_active",
        "count":   "50",
        "lang":    "en-US",
        "region":  "US",
    }

    for url in endpoints:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=12)
            if not resp.ok:
                continue
            data   = resp.json()
            quotes = (
                data.get("finance", {})
                    .get("result", [{}])[0]
                    .get("quotes", [])
            )
            if quotes:
                return quotes
        except Exception:
            continue

    return []

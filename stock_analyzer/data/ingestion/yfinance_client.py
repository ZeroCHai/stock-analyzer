"""Fetch US stock data from Yahoo Finance and persist to SQLite.

Falls back to demo data automatically when the network is unavailable.
Set DEMO_MODE=true in environment (or .env) to force demo mode.
"""

import os
import yfinance as yf
import pandas as pd
from stock_analyzer.data.db import upsert_stock, upsert_financials, get_financials
from stock_analyzer.data.ingestion.demo_data import DEMO_STOCKS, get_demo_history

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


def fetch_news(symbol: str, max_items: int = 15) -> list:
    """Return recent news for a symbol as a list of dicts from Yahoo Finance."""
    if is_demo_mode():
        return []
    try:
        news = yf.Ticker(symbol.upper()).news or []
        return news[:max_items]
    except Exception:
        return []


def fetch_industry_news(sector: str, max_items: int = 15) -> list:
    """Return news for the SPDR sector ETF matching the given sector name."""
    etf = SECTOR_ETF.get(sector, "")
    if not etf:
        return []
    return fetch_news(etf, max_items)

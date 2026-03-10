"""Fetch US stock data from Yahoo Finance and persist to SQLite."""

import yfinance as yf
import pandas as pd
from stock_analyzer.data.db import upsert_stock, upsert_financials, get_financials


def fetch_stock(symbol: str, force: bool = False) -> dict:
    """
    Return the .info dict for a symbol.
    Uses SQLite cache unless force=True.
    """
    symbol = symbol.upper()

    if not force:
        cached = get_financials(symbol)
        if cached:
            return cached

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


def fetch_price_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Return OHLCV history as a DataFrame."""
    return yf.Ticker(symbol.upper()).history(period=period)


def fetch_income_statement(symbol: str) -> pd.DataFrame:
    return yf.Ticker(symbol.upper()).financials


def fetch_balance_sheet(symbol: str) -> pd.DataFrame:
    return yf.Ticker(symbol.upper()).balance_sheet


def fetch_cash_flow(symbol: str) -> pd.DataFrame:
    return yf.Ticker(symbol.upper()).cashflow

"""
Stock screener — filter a list of symbols by fundamental criteria.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from stock_analyzer.data.ingestion.yfinance_client import fetch_stock
from stock_analyzer.analysis.fundamental import extract_metrics


@dataclass
class ScreenerCriteria:
    # Valuation
    max_pe:            float | None = None
    max_pb:            float | None = None
    max_ps:            float | None = None

    # Profitability
    min_roe:           float | None = None   # e.g. 0.15 = 15%
    min_net_margin:    float | None = None

    # Growth
    min_revenue_growth: float | None = None  # e.g. 0.10 = 10%

    # Safety
    max_debt_to_equity: float | None = None  # e.g. 100
    min_current_ratio:  float | None = None

    # Dividend
    min_dividend_yield: float | None = None

    # Market cap (USD)
    min_market_cap:    float | None = None
    max_market_cap:    float | None = None


def _passes(metrics: dict, c: ScreenerCriteria) -> bool:
    def check(key, threshold, op):
        v = metrics.get(key)
        if v is None:
            return True  # unknown → don't filter out
        return op(v, threshold)

    checks = [
        (c.max_pe,             "pe_ratio",          lambda v, t: v <= t),
        (c.max_pb,             "pb_ratio",           lambda v, t: v <= t),
        (c.max_ps,             "ps_ratio",           lambda v, t: v <= t),
        (c.min_roe,            "roe",                lambda v, t: v >= t),
        (c.min_net_margin,     "net_margin",         lambda v, t: v >= t),
        (c.min_revenue_growth, "revenue_growth",     lambda v, t: v >= t),
        (c.max_debt_to_equity, "debt_to_equity",     lambda v, t: v <= t),
        (c.min_current_ratio,  "current_ratio",      lambda v, t: v >= t),
        (c.min_dividend_yield, "dividend_yield",     lambda v, t: v >= t),
        (c.min_market_cap,     "market_cap",         lambda v, t: v >= t),
        (c.max_market_cap,     "market_cap",         lambda v, t: v <= t),
    ]

    for threshold, key, op in checks:
        if threshold is not None:
            if not check(key, threshold, op):
                return False
    return True


def screen(symbols: list[str], criteria: ScreenerCriteria) -> list[dict]:
    """
    Run the screener against a list of ticker symbols.
    Returns a list of dicts: {symbol, name, ...metrics}
    Symbols that fail to fetch are silently skipped.
    """
    results = []
    for symbol in symbols:
        try:
            info = fetch_stock(symbol)
        except Exception:
            continue

        metrics = extract_metrics(info)
        if _passes(metrics, criteria):
            row = {
                "symbol":  symbol,
                "name":    info.get("longName", symbol),
                "sector":  info.get("sector", ""),
                **metrics,
            }
            results.append(row)

    return results

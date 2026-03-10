"""
Extract and normalise fundamental metrics from a yfinance .info dict.
All values are returned as floats; None means data unavailable.
"""

from __future__ import annotations


def extract_metrics(info: dict) -> dict:
    """Return a flat dict of key fundamental indicators."""

    def _get(key) -> float | None:
        v = info.get(key)
        return float(v) if v is not None else None

    return {
        # Valuation
        "pe_ratio":               _get("trailingPE"),
        "forward_pe":             _get("forwardPE"),
        "pb_ratio":               _get("priceToBook"),
        "ps_ratio":               _get("priceToSalesTrailing12Months"),
        "ev_ebitda":              _get("enterpriseToEbitda"),
        "peg_ratio":              _get("pegRatio"),

        # Profitability
        "gross_margin":           _get("grossMargins"),
        "operating_margin":       _get("operatingMargins"),
        "net_margin":             _get("profitMargins"),
        "roe":                    _get("returnOnEquity"),
        "roa":                    _get("returnOnAssets"),

        # Growth (YoY)
        "revenue_growth":         _get("revenueGrowth"),
        "earnings_growth":        _get("earningsGrowth"),

        # Financial health
        "current_ratio":          _get("currentRatio"),
        "debt_to_equity":         _get("debtToEquity"),
        "free_cashflow":          _get("freeCashflow"),

        # Dividends
        "dividend_yield":         _get("dividendYield"),
        "payout_ratio":           _get("payoutRatio"),

        # Per share
        "eps_ttm":                _get("trailingEps"),
        "eps_forward":            _get("forwardEps"),
        "book_value_per_share":   _get("bookValue"),

        # Market data
        "market_cap":             _get("marketCap"),
        "beta":                   _get("beta"),
        "52w_high":               _get("fiftyTwoWeekHigh"),
        "52w_low":                _get("fiftyTwoWeekLow"),
        "current_price":          _get("currentPrice"),
    }


def score_health(metrics: dict) -> dict[str, str]:
    """
    Quick-and-dirty colour-coded health flags for key ratios.
    Returns {metric_key: "green" | "yellow" | "red" | "gray"}.
    """
    flags = {}

    def flag(key, good, bad, reverse=False):
        v = metrics.get(key)
        if v is None:
            flags[key] = "gray"
            return
        if reverse:
            flags[key] = "green" if v <= good else ("red" if v >= bad else "yellow")
        else:
            flags[key] = "green" if v >= good else ("red" if v <= bad else "yellow")

    flag("roe",              good=0.15, bad=0.05)
    flag("net_margin",       good=0.10, bad=0.02)
    flag("current_ratio",    good=2.0,  bad=1.0)
    flag("debt_to_equity",   good=50,   bad=200,  reverse=True)
    flag("revenue_growth",   good=0.10, bad=0.00)
    flag("gross_margin",     good=0.30, bad=0.10)

    return flags


METRIC_LABELS = {
    "pe_ratio":             "P/E (TTM)",
    "forward_pe":           "Forward P/E",
    "pb_ratio":             "P/B",
    "ps_ratio":             "P/S",
    "ev_ebitda":            "EV/EBITDA",
    "peg_ratio":            "PEG",
    "gross_margin":         "Gross Margin",
    "operating_margin":     "Operating Margin",
    "net_margin":           "Net Margin",
    "roe":                  "ROE",
    "roa":                  "ROA",
    "revenue_growth":       "Revenue Growth (YoY)",
    "earnings_growth":      "Earnings Growth (YoY)",
    "current_ratio":        "Current Ratio",
    "debt_to_equity":       "Debt / Equity",
    "free_cashflow":        "Free Cash Flow",
    "dividend_yield":       "Dividend Yield",
    "payout_ratio":         "Payout Ratio",
    "eps_ttm":              "EPS (TTM)",
    "eps_forward":          "EPS (Forward)",
    "book_value_per_share": "Book Value / Share",
    "market_cap":           "Market Cap",
    "beta":                 "Beta",
    "52w_high":             "52W High",
    "52w_low":              "52W Low",
    "current_price":        "Price",
}

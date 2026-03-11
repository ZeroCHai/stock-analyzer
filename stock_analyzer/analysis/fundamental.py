"""
Extract and normalise fundamental metrics from a yfinance .info dict.
All values are returned as floats; None means data unavailable.
"""

from __future__ import annotations
import pandas as pd


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


def extract_historical_metrics(income_stmt, balance_sheet, cash_flow) -> dict:
    """
    Extract key financial metrics for up to 3 fiscal years.
    Input DataFrames are from yfinance (rows=metrics, columns=fiscal year dates).
    Returns {metric_key: {year_str: float}}.
    """
    def safe_row(df, *candidates):
        if df is None or df.empty:
            return None
        for key in candidates:
            if key in df.index:
                return df.loc[key]
        return None

    def to_year(col) -> str:
        try:
            return str(col.year)
        except AttributeError:
            return str(col)[:4]

    def series_to_dict(series, cols) -> dict:
        if series is None:
            return {}
        out = {}
        for col in cols:
            try:
                v = series[col]
                if not pd.isna(v):
                    out[to_year(col)] = float(v)
            except (KeyError, TypeError):
                pass
        return out

    def margin_dict(num, den, cols) -> dict:
        out = {}
        if num is None or den is None:
            return out
        for col in cols:
            try:
                n, d = num[col], den[col]
                if not pd.isna(n) and not pd.isna(d) and d != 0:
                    out[to_year(col)] = float(n) / float(d)
            except (KeyError, TypeError):
                pass
        return out

    inc_cols = list(income_stmt.columns[:3]) if (income_stmt is not None and not income_stmt.empty) else []
    bs_cols  = list(balance_sheet.columns[:3]) if (balance_sheet is not None and not balance_sheet.empty) else []
    cf_cols  = list(cash_flow.columns[:3]) if (cash_flow is not None and not cash_flow.empty) else []

    result = {}

    # ── Income Statement ──────────────────────────────────────────────────────
    revenue    = safe_row(income_stmt, "Total Revenue")
    gross_p    = safe_row(income_stmt, "Gross Profit")
    op_income  = safe_row(income_stmt, "Operating Income", "EBIT")
    net_income = safe_row(income_stmt, "Net Income")
    ebitda     = safe_row(income_stmt, "EBITDA", "Normalized EBITDA")
    eps        = safe_row(income_stmt, "Diluted EPS", "Basic EPS")

    result["revenue"]           = series_to_dict(revenue, inc_cols)
    result["gross_profit"]      = series_to_dict(gross_p, inc_cols)
    result["operating_income"]  = series_to_dict(op_income, inc_cols)
    result["net_income"]        = series_to_dict(net_income, inc_cols)
    result["ebitda"]            = series_to_dict(ebitda, inc_cols)
    result["eps_hist"]          = series_to_dict(eps, inc_cols)

    result["gross_margin_hist"]     = margin_dict(gross_p, revenue, inc_cols)
    result["operating_margin_hist"] = margin_dict(op_income, revenue, inc_cols)
    result["net_margin_hist"]       = margin_dict(net_income, revenue, inc_cols)

    # ── Balance Sheet ─────────────────────────────────────────────────────────
    total_assets = safe_row(balance_sheet, "Total Assets")
    total_equity = safe_row(balance_sheet, "Stockholders Equity", "Common Stock Equity")
    total_debt   = safe_row(balance_sheet, "Total Debt")

    result["total_assets"] = series_to_dict(total_assets, bs_cols)
    result["total_equity"] = series_to_dict(total_equity, bs_cols)
    result["total_debt"]   = series_to_dict(total_debt, bs_cols)

    # ── ROE (cross-statement, match by year string) ───────────────────────────
    roe = {}
    for yr in set(result["net_income"]) & set(result["total_equity"]):
        e = result["total_equity"][yr]
        if e != 0:
            roe[yr] = result["net_income"][yr] / e
    result["roe_hist"] = roe

    # ── Cash Flow ─────────────────────────────────────────────────────────────
    op_cf = safe_row(cash_flow, "Operating Cash Flow")
    capex = safe_row(cash_flow, "Capital Expenditure")
    fcf   = safe_row(cash_flow, "Free Cash Flow")

    result["operating_cashflow"] = series_to_dict(op_cf, cf_cols)
    result["capex"]              = series_to_dict(capex, cf_cols)
    result["free_cashflow_hist"] = series_to_dict(fcf, cf_cols)

    # Derive FCF if not directly available
    if not result["free_cashflow_hist"] and op_cf is not None and capex is not None:
        fcf_calc = {}
        for col in cf_cols:
            try:
                o, c = op_cf[col], capex[col]
                if not pd.isna(o) and not pd.isna(c):
                    fcf_calc[to_year(col)] = float(o) + float(c)  # capex is negative
            except (KeyError, TypeError):
                pass
        result["free_cashflow_hist"] = fcf_calc

    return result


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

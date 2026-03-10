"""
Local file ingestion — CSV (primary) with Bloomberg / Wind export support.

Supported sources (auto-detected):
  1. Standard CSV  — field names follow the project's own schema (see below)
  2. Bloomberg export — BDH/BCDE terminal exports
  3. Wind export   — Wind金融终端 英文/中文 导出

Output: dict compatible with yfinance .info keys, so the existing
        fundamental.py / screener.py pipeline works without changes.

Standard CSV schema
───────────────────
Required columns:
  symbol, period (YYYY-MM-DD), revenue, net_income, total_assets, total_equity

Optional (used to compute ratios):
  gross_profit, operating_income, total_debt, free_cashflow,
  eps, shares_outstanding, current_assets, current_liabilities,
  dividends_paid, current_price

Usage
─────
  from stock_analyzer.data.ingestion.local import load_local_data

  # Load most-recent period for one symbol
  data = load_local_data("path/to/file.csv", symbol="AAPL")

  # Or load all symbols in file as {symbol: info_dict}
  all_data = load_local_data("path/to/file.csv")
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path


# ── Field maps ────────────────────────────────────────────────────────────────

# Maps source column names → internal standard names
_BLOOMBERG_MAP = {
    # Revenue
    "SALES_REV_TURN":           "revenue",
    "NET_REVENUE":              "revenue",
    "REVENUE":                  "revenue",
    # Net income
    "NET_INCOME":               "net_income",
    "NET_INCOME_CONT_OPS":      "net_income",
    # Gross profit
    "GROSS_PROFIT":             "gross_profit",
    # Operating income
    "EBIT":                     "operating_income",
    "IS_OPER_INC":              "operating_income",
    # Balance sheet
    "BS_TOT_ASSET":             "total_assets",
    "TOT_COMMON_EQY":           "total_equity",
    "SHORT_AND_LONG_TERM_DEBT": "total_debt",
    "BS_LT_BORROW":             "total_debt",          # fallback
    "BS_CUR_ASSET_REPORT":      "current_assets",
    "BS_CUR_LIAB":              "current_liabilities",
    # Cash flow
    "CF_FREE_CASH_FLOW":        "free_cashflow",
    "CF_LEVERED_FREE_CASH_FLOW":"free_cashflow",
    # Per share
    "IS_EPS":                   "eps",
    "EQY_SH_OUT":               "shares_outstanding",
    # Dividends
    "CF_DVD_PAID":              "dividends_paid",
    # Price (if included in export)
    "PX_LAST":                  "current_price",
    "LAST_PRICE":               "current_price",
    # Date
    "DATES":                    "period",
    "DATE":                     "period",
}

_WIND_MAP = {
    # Chinese field names (Wind中文导出)
    "营业收入":     "revenue",
    "净利润":       "net_income",
    "毛利润":       "gross_profit",
    "营业利润":     "operating_income",
    "总资产":       "total_assets",
    "股东权益合计":  "total_equity",
    "股东权益":     "total_equity",
    "有息负债":     "total_debt",
    "总负债":       "total_debt",
    "流动资产":     "current_assets",
    "流动负债":     "current_liabilities",
    "自由现金流":   "free_cashflow",
    "每股收益":     "eps",
    "总股本":       "shares_outstanding",
    "股息":         "dividends_paid",
    "收盘价":       "current_price",
    "报告期":       "period",
    "代码":         "symbol",
    "股票代码":     "symbol",
    # Wind English export
    "OPERATING REVENUE":   "revenue",
    "NET PROFIT":          "net_income",
    "GROSS PROFIT":        "gross_profit",
    "OPERATING PROFIT":    "operating_income",
    "TOTAL ASSETS":        "total_assets",
    "TOTAL EQUITY":        "total_equity",
    "TOTAL DEBT":          "total_debt",
    "CURRENT ASSETS":      "current_assets",
    "CURRENT LIABILITIES": "current_liabilities",
    "FREE CASH FLOW":      "free_cashflow",
    "EPS":                 "eps",
    "SHARES OUTSTANDING":  "shares_outstanding",
    "CLOSE PRICE":         "current_price",
    "REPORT DATE":         "period",
    "WIND CODE":           "symbol",
    "TICKER":              "symbol",
}


# ── Format detection ──────────────────────────────────────────────────────────

def _detect_format(columns: list[str]) -> str:
    """Return 'bloomberg', 'wind', or 'standard'."""
    upper = {c.upper() for c in columns}
    bloomberg_signals = {"BS_TOT_ASSET", "SALES_REV_TURN", "IS_EPS", "PX_LAST"}
    wind_signals      = {"营业收入", "净利润", "总资产", "WIND CODE", "OPERATING REVENUE"}

    if bloomberg_signals & upper:
        return "bloomberg"
    if wind_signals & {c.upper() for c in columns} | set(columns):
        # Wind uses exact Chinese chars, so check both
        if any(c in _WIND_MAP for c in columns):
            return "wind"
    return "standard"


def _rename(df: pd.DataFrame, field_map: dict) -> pd.DataFrame:
    """Rename columns using a field map (case-insensitive for the map keys)."""
    upper_map = {k.upper(): v for k, v in field_map.items()}
    rename = {}
    for col in df.columns:
        target = upper_map.get(col.upper()) or field_map.get(col)
        if target:
            rename[col] = target
    return df.rename(columns=rename)


# ── Ratio computation ─────────────────────────────────────────────────────────

def _compute_ratios(row: pd.Series) -> dict:
    """
    Derive yfinance-compatible ratio keys from raw financials.
    Missing inputs produce None (not errors).
    """
    def _s(key) -> float | None:
        v = row.get(key)
        return float(v) if pd.notna(v) and v != 0 else None

    rev   = _s("revenue")
    ni    = _s("net_income")
    gp    = _s("gross_profit")
    oi    = _s("operating_income")
    ta    = _s("total_assets")
    eq    = _s("total_equity")
    td    = _s("total_debt")
    ca    = _s("current_assets")
    cl    = _s("current_liabilities")
    fcf   = _s("free_cashflow")
    eps   = _s("eps")
    price = _s("current_price")
    divs  = _s("dividends_paid")
    shares = _s("shares_outstanding")

    def _div(a, b):
        if a is not None and b:
            return a / b
        return None

    pe  = _div(price, eps)
    pb  = _div(price, _div(eq, shares)) if eq and shares else None
    bvps = _div(eq, shares)

    return {
        # Margins
        "grossMargins":      _div(gp, rev),
        "operatingMargins":  _div(oi, rev),
        "profitMargins":     _div(ni, rev),
        # Returns
        "returnOnEquity":    _div(ni, eq),
        "returnOnAssets":    _div(ni, ta),
        # Valuation (only if price included)
        "trailingPE":        pe,
        "priceToBook":       pb,
        "bookValue":         bvps,
        "trailingEps":       eps,
        # Leverage / liquidity
        "currentRatio":      _div(ca, cl),
        "debtToEquity":      (_div(td, eq) * 100) if td and eq else None,
        # Cash flow
        "freeCashflow":      fcf,
        # Dividend
        "dividendYield":     _div(abs(divs), _div(price * shares, 1)) if divs and price and shares else None,
        # Market data
        "currentPrice":      price,
        # Raw (stored for reference)
        "_revenue":          rev,
        "_net_income":       ni,
        "_total_assets":     ta,
        "_total_equity":     eq,
    }


# ── Public interface ──────────────────────────────────────────────────────────

def load_local_data(
    file_path: str,
    symbol: str | None = None,
) -> dict:
    """
    Load a CSV (or Excel) file and return a yfinance-compatible info dict.

    Parameters
    ----------
    file_path : str
        Path to .csv or .xlsx file.
    symbol : str | None
        If provided, filter to this ticker and return a single dict.
        If None and the file has multiple symbols, returns {symbol: dict}.

    Returns
    -------
    dict  — if symbol is specified or file has exactly one symbol
    dict[str, dict]  — if multiple symbols and symbol=None
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .csv or .xlsx")

    df.columns = df.columns.str.strip()

    fmt = _detect_format(df.columns.tolist())
    if fmt == "bloomberg":
        df = _rename(df, _BLOOMBERG_MAP)
    elif fmt == "wind":
        df = _rename(df, _WIND_MAP)
    # else: standard — use as-is

    # Normalise column names to lowercase stripped
    df.columns = [c.lower().strip() for c in df.columns]

    # Convert numeric columns
    for col in df.columns:
        if col not in ("symbol", "period"):
            df[col] = pd.to_numeric(df[col].str.replace(",", ""), errors="coerce")

    # Filter by symbol if requested
    if symbol:
        symbol = symbol.upper()
        if "symbol" in df.columns:
            df = df[df["symbol"].str.upper() == symbol]
        if df.empty:
            raise ValueError(f"Symbol '{symbol}' not found in {file_path}")

    # Sort by period desc, take most recent row per symbol
    if "period" in df.columns:
        df["period"] = pd.to_datetime(df["period"], errors="coerce")
        df = df.sort_values("period", ascending=False)

    if "symbol" not in df.columns:
        # Single-company file: inject symbol
        df["symbol"] = symbol or path.stem.split("_")[0].upper()

    # Build output
    results = {}
    for sym, group in df.groupby("symbol"):
        row = group.iloc[0]  # most recent period
        ratios = _compute_ratios(row)
        info = {
            "symbol":   str(sym).upper(),
            "longName": str(sym).upper(),
            "_source":  f"local:{fmt}",
            **ratios,
        }
        results[str(sym).upper()] = info

    if symbol:
        return results[symbol.upper()]

    if len(results) == 1:
        return next(iter(results.values()))

    return results

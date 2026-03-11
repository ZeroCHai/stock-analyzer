"""
Streamlit UI — US Stock Fundamental Analyzer
Run:  streamlit run stock_analyzer/ui/app.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from stock_analyzer.data.db import init_db
from stock_analyzer.data.ingestion.yfinance_client import (
    fetch_stock, fetch_price_history, set_demo_mode, is_demo_mode,
    fetch_income_statement, fetch_balance_sheet, fetch_cash_flow,
    fetch_news, fetch_industry_news, SECTOR_ETF,
    fetch_sector_peers_news, fetch_peers_news_by_list, SECTOR_PEERS,
)
from stock_analyzer.data.ingestion.demo_data import DEMO_STOCKS
from stock_analyzer.analysis.fundamental import (
    extract_metrics, score_health, METRIC_LABELS, extract_historical_metrics,
)
from stock_analyzer.analysis.screener import ScreenerCriteria, screen
from stock_analyzer.analysis.ai import (
    analyze_stock_stream, compare_stocks_stream, analyze_financials_stream,
    analyze_stock_news_stream, analyze_industry_stream,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _render_news_item(item: dict):
    """Render one Yahoo Finance news item."""
    title     = item.get("title", "Untitled")
    link      = item.get("link", "")
    publisher = item.get("publisher", "")
    ts        = item.get("providerPublishTime", 0)
    date_str  = datetime.fromtimestamp(ts).strftime("%b %d, %Y") if ts else ""
    tickers   = item.get("relatedTickers", [])

    if link:
        st.markdown(f"**[{title}]({link})**")
    else:
        st.markdown(f"**{title}**")
    meta = f"_{publisher}_"
    if date_str:
        meta += f" · {date_str}"
    if tickers:
        meta += f" · {' '.join(tickers[:6])}"
    st.caption(meta)
    st.divider()


def _bar_chart(data: dict, title: str, pct: bool = False, billions: bool = False) -> "go.Figure":
    """Simple bar chart for {year_str: float} data."""
    years = sorted(data.keys())
    vals  = [data[y] for y in years]
    if billions:
        vals   = [v / 1e9 for v in vals]
        ylabel = "USD (B)"
    elif pct:
        vals   = [v * 100 for v in vals]
        ylabel = "%"
    else:
        ylabel = ""
    colors = ["#d62728" if v < 0 else "#1f77b4" for v in vals]
    fig = go.Figure(go.Bar(
        x=years, y=vals, marker_color=colors,
        text=[f"{v:.1f}" for v in vals], textposition="outside",
    ))
    fig.update_layout(
        title=title, yaxis_title=ylabel,
        template="plotly_white", height=280,
        margin=dict(l=0, r=0, t=40, b=20),
    )
    return fig


# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
st.set_page_config(page_title="Stock Analyzer", page_icon="📈", layout="wide")

# ── Robinhood-style CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Buttons ── */
.stButton > button {
    background-color: #00C805;
    color: #000000;
    font-weight: 700;
    border: none;
    border-radius: 24px;
    padding: 0.5rem 1.8rem;
    transition: background-color 0.15s ease;
}
.stButton > button:hover { background-color: #00A804; color: #000000; }
.stButton > button:active { background-color: #008F03; color: #000000; }

/* ── Metric labels ── */
[data-testid="stMetricLabel"] { font-size: 0.75rem; color: #888888; letter-spacing: 0.04em; }
[data-testid="stMetricValue"] { font-size: 1.35rem; font-weight: 700; }

/* ── Dividers ── */
hr { border-color: #2A2A32 !important; margin: 0.6rem 0; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.03em;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border-radius: 8px; }

/* ── Sidebar nav ── */
[data-testid="stSidebar"] .stRadio label { font-size: 0.88rem; font-weight: 500; }

/* ── Input fields ── */
[data-testid="stTextInput"] input { border-radius: 8px; }

/* ── Expander ── */
[data-testid="stExpander"] summary { font-weight: 600; }

/* ── Save as PDF button ── */
.pdf-btn {
    position: fixed;
    top: 14px;
    right: 16px;
    z-index: 9999;
    background-color: #1f77b4;
    color: #ffffff;
    font-weight: 700;
    font-size: 0.8rem;
    border: none;
    border-radius: 20px;
    padding: 0.4rem 1.1rem;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    transition: background-color 0.15s ease;
}
.pdf-btn:hover { background-color: #1560a0; }

/* ── Print styles ── */
@media print {
    .pdf-btn { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    header { display: none !important; }
    footer { display: none !important; }
    .stDeployButton { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding: 1rem !important; max-width: 100% !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<button class="pdf-btn" onclick="window.print()">⬇ Save as PDF</button>',
    unsafe_allow_html=True,
)

# ── Demo mode toggle (sidebar) ────────────────────────────────────────────────
st.sidebar.divider()
demo = st.sidebar.toggle(
    "Demo Mode (no network)",
    value=is_demo_mode(),
    help="Use built-in sample data (AAPL, MSFT, NVDA, GOOGL, JPM). "
         "Disable to fetch live data from Yahoo Finance.",
)
set_demo_mode(demo)
if demo:
    st.sidebar.caption(f"Demo symbols: {', '.join(sorted(DEMO_STOCKS))}")
st.sidebar.divider()

# ── Sidebar navigation ────────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigation",
    ["📊 Stock Overview", "🔍 Screener", "🤖 AI Analysis", "📑 Financial Analysis",
     "📰 Stock News", "🏭 Industry", "⚖️ Compare"],
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — Stock Overview
# ─────────────────────────────────────────────────────────────────────────────
if page == "📊 Stock Overview":
    st.title("📊 Stock Overview")
    symbol = st.text_input("Enter ticker symbol (e.g. AAPL, MSFT, NVDA)").strip().upper()

    if symbol:
        with st.spinner(f"Fetching {symbol}…"):
            try:
                info = fetch_stock(symbol)
            except Exception as e:
                st.error(str(e))
                st.stop()

        metrics = extract_metrics(info)
        flags   = score_health(metrics)

        # Header
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.subheader(info.get("longName", symbol))
            st.caption(f"{info.get('sector','')} · {info.get('industry','')}")
        with col2:
            price = metrics.get("current_price")
            st.metric("Price", f"${price:.2f}" if price else "N/A")
        with col3:
            mcap = metrics.get("market_cap")
            st.metric("Market Cap", f"${mcap/1e9:.1f}B" if mcap else "N/A")

        st.divider()

        # Fundamentals table
        st.subheader("Key Metrics")
        COLOR_MAP = {"green": "🟢", "yellow": "🟡", "red": "🔴", "gray": "⚪"}

        display_keys = [
            "pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda",
            "gross_margin", "operating_margin", "net_margin",
            "roe", "roa",
            "revenue_growth", "earnings_growth",
            "current_ratio", "debt_to_equity",
            "dividend_yield", "beta",
        ]

        rows = []
        for key in display_keys:
            v = metrics.get(key)
            if v is None:
                continue
            flag = flags.get(key, "gray")
            if key in ("gross_margin", "operating_margin", "net_margin",
                       "roe", "roa", "revenue_growth", "earnings_growth",
                       "dividend_yield"):
                formatted = f"{v:.1%}"
            else:
                formatted = f"{v:.2f}"
            rows.append({
                "":        COLOR_MAP[flag],
                "Metric":  METRIC_LABELS[key],
                "Value":   formatted,
            })

        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        # 3-Year Historical Trends
        st.subheader("3-Year Historical Trends")
        with st.spinner("Loading financial history…"):
            try:
                inc = fetch_income_statement(symbol)
                bs  = fetch_balance_sheet(symbol)
                cf  = fetch_cash_flow(symbol)
                hist = extract_historical_metrics(inc, bs, cf)
            except Exception:
                hist = {}

        has_hist = any(v for v in hist.values())
        if not has_hist:
            st.caption("Historical financials not available (demo mode or data missing).")
        else:
            c1, c2 = st.columns(2)
            with c1:
                if hist.get("revenue"):
                    st.plotly_chart(_bar_chart(hist["revenue"], "Revenue ($B)", billions=True),
                                    use_container_width=True)
                if hist.get("eps_hist"):
                    st.plotly_chart(_bar_chart(hist["eps_hist"], "EPS – Diluted ($)"),
                                    use_container_width=True)
                if hist.get("free_cashflow_hist"):
                    st.plotly_chart(_bar_chart(hist["free_cashflow_hist"], "Free Cash Flow ($B)", billions=True),
                                    use_container_width=True)
            with c2:
                if hist.get("net_income"):
                    st.plotly_chart(_bar_chart(hist["net_income"], "Net Income ($B)", billions=True),
                                    use_container_width=True)
                # Margins overlay
                margin_data = {
                    k: hist[k] for k in ("gross_margin_hist", "operating_margin_hist", "net_margin_hist")
                    if hist.get(k)
                }
                if margin_data:
                    fig_m = go.Figure()
                    margin_labels = {
                        "gross_margin_hist": "Gross Margin",
                        "operating_margin_hist": "Operating Margin",
                        "net_margin_hist": "Net Margin",
                    }
                    colors_m = ["#2ca02c", "#ff7f0e", "#1f77b4"]
                    for (key, label), color in zip(margin_labels.items(), colors_m):
                        d = hist.get(key, {})
                        if d:
                            yrs = sorted(d.keys())
                            fig_m.add_trace(go.Scatter(
                                x=yrs, y=[d[y] * 100 for y in yrs],
                                mode="lines+markers", name=label,
                                line=dict(color=color),
                            ))
                    fig_m.update_layout(
                        title="Margin Trends (%)", yaxis_title="%",
                        template="plotly_white", height=280,
                        margin=dict(l=0, r=0, t=40, b=20),
                    )
                    st.plotly_chart(fig_m, use_container_width=True)
                if hist.get("roe_hist"):
                    st.plotly_chart(_bar_chart(hist["roe_hist"], "Return on Equity (%)", pct=True),
                                    use_container_width=True)

        st.divider()

        # Price chart
        st.subheader("Price History (1 Year)")
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
        hist = fetch_price_history(symbol, period=period)
        if not hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["Close"],
                mode="lines", name="Close",
                line=dict(color="#1f77b4", width=2)
            ))
            fig.update_layout(
                xaxis_title="Date", yaxis_title="Price (USD)",
                template="plotly_white", height=350,
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Business summary
        summary = info.get("longBusinessSummary", "")
        if summary:
            with st.expander("Business Description"):
                st.write(summary)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — Screener
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔍 Screener":
    st.title("🔍 Stock Screener")
    st.caption("Enter a list of tickers to screen, then set filter criteria.")

    symbols_raw = st.text_area(
        "Tickers (comma or newline separated)",
        "AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, JPM, JNJ, V",
        height=80,
    )
    symbols = [s.strip().upper() for s in symbols_raw.replace("\n", ",").split(",") if s.strip()]

    st.subheader("Filters")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Valuation**")
        max_pe = st.number_input("Max P/E", min_value=0.0, value=0.0, step=1.0)
        max_pb = st.number_input("Max P/B", min_value=0.0, value=0.0, step=0.5)

    with c2:
        st.markdown("**Profitability**")
        min_roe = st.number_input("Min ROE (%)", min_value=0.0, value=0.0, step=1.0)
        min_margin = st.number_input("Min Net Margin (%)", min_value=0.0, value=0.0, step=1.0)

    with c3:
        st.markdown("**Health**")
        max_de = st.number_input("Max Debt/Equity", min_value=0.0, value=0.0, step=10.0)
        min_growth = st.number_input("Min Revenue Growth (%)", min_value=0.0, value=0.0, step=1.0)

    if st.button("Run Screener", type="primary"):
        criteria = ScreenerCriteria(
            max_pe=max_pe if max_pe > 0 else None,
            max_pb=max_pb if max_pb > 0 else None,
            min_roe=min_roe / 100 if min_roe > 0 else None,
            min_net_margin=min_margin / 100 if min_margin > 0 else None,
            max_debt_to_equity=max_de if max_de > 0 else None,
            min_revenue_growth=min_growth / 100 if min_growth > 0 else None,
        )

        with st.spinner("Screening…"):
            results = screen(symbols, criteria)

        if not results:
            st.warning("No stocks matched the criteria.")
        else:
            st.success(f"{len(results)} stock(s) passed the screen.")
            cols_to_show = [
                "symbol", "name", "sector",
                "pe_ratio", "pb_ratio", "roe", "net_margin",
                "revenue_growth", "debt_to_equity", "market_cap",
            ]
            df = pd.DataFrame(results)
            df = df[[c for c in cols_to_show if c in df.columns]]

            # Format
            for pct_col in ("roe", "net_margin", "revenue_growth"):
                if pct_col in df.columns:
                    df[pct_col] = df[pct_col].apply(
                        lambda v: f"{v:.1%}" if pd.notna(v) else "N/A"
                    )
            if "market_cap" in df.columns:
                df["market_cap"] = df["market_cap"].apply(
                    lambda v: f"${v/1e9:.1f}B" if pd.notna(v) else "N/A"
                )
            for ratio_col in ("pe_ratio", "pb_ratio", "debt_to_equity"):
                if ratio_col in df.columns:
                    df[ratio_col] = df[ratio_col].apply(
                        lambda v: f"{v:.2f}" if pd.notna(v) else "N/A"
                    )

            st.dataframe(df, hide_index=True, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — AI Analysis
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🤖 AI Analysis":
    st.title("🤖 AI Fundamental Analysis")
    st.caption("Powered by Ark Seed 2.0.")

    symbol = st.text_input("Ticker symbol").strip().upper()

    if symbol and st.button("Generate Report", type="primary"):
        with st.spinner(f"Fetching {symbol}…"):
            try:
                info = fetch_stock(symbol)
            except Exception as e:
                st.error(str(e))
                st.stop()

        st.subheader(f"Analysis: {info.get('longName', symbol)}")
        report_area = st.empty()
        full_text = ""

        with st.spinner("Claude is thinking…"):
            for chunk in analyze_stock_stream(info):
                full_text += chunk
                report_area.markdown(full_text + "▌")

        report_area.markdown(full_text)
        st.success("Report complete.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 — Financial Analysis
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📑 Financial Analysis":
    st.title("📑 Financial Analysis")
    st.caption("3-year financial statements and AI-powered trend analysis for a single stock.")

    symbol = st.text_input("Ticker symbol", key="fin_ticker").strip().upper()

    if symbol and st.button("Load Financials", type="primary"):
        with st.spinner(f"Fetching {symbol}…"):
            try:
                info = fetch_stock(symbol)
                inc  = fetch_income_statement(symbol)
                bs   = fetch_balance_sheet(symbol)
                cf   = fetch_cash_flow(symbol)
                hist = extract_historical_metrics(inc, bs, cf)
            except Exception as e:
                st.error(str(e))
                st.stop()

        company_name = info.get("longName", symbol)
        sector       = info.get("sector", "N/A")
        st.subheader(company_name)
        st.caption(f"{sector} · {info.get('industry', '')}")

        has_hist = any(v for v in hist.values())
        if not has_hist:
            st.warning("Historical financial data not available (demo mode or data missing).")
            st.stop()

        # ── 3-Year Summary Table ───────────────────────────────────────────
        st.subheader("3-Year Financial Summary")

        all_years = sorted({
            yr
            for key in ("revenue", "net_income", "eps_hist", "gross_margin_hist",
                        "operating_margin_hist", "net_margin_hist", "roe_hist",
                        "total_assets", "total_debt", "free_cashflow_hist")
            for yr in hist.get(key, {}).keys()
        })

        summary_rows = []
        def _pct_change(d, years):
            if len(years) >= 2:
                v0, v1 = d.get(years[0]), d.get(years[-1])
                if v0 and v1 and v0 != 0:
                    return f"{(v1-v0)/abs(v0):+.1%}"
            return "—"

        metric_display = [
            ("revenue",              "Revenue",           lambda v: f"${v/1e9:.1f}B",  False),
            ("gross_profit",         "Gross Profit",      lambda v: f"${v/1e9:.1f}B",  False),
            ("gross_margin_hist",    "Gross Margin",      lambda v: f"{v:.1%}",         True),
            ("operating_income",     "Operating Income",  lambda v: f"${v/1e9:.1f}B",  False),
            ("operating_margin_hist","Operating Margin",  lambda v: f"{v:.1%}",         True),
            ("net_income",           "Net Income",        lambda v: f"${v/1e9:.1f}B",  False),
            ("net_margin_hist",      "Net Margin",        lambda v: f"{v:.1%}",         True),
            ("ebitda",               "EBITDA",            lambda v: f"${v/1e9:.1f}B",  False),
            ("eps_hist",             "EPS (Diluted)",     lambda v: f"${v:.2f}",        False),
            ("total_assets",         "Total Assets",      lambda v: f"${v/1e9:.1f}B",  False),
            ("total_debt",           "Total Debt",        lambda v: f"${v/1e9:.1f}B",  False),
            ("total_equity",         "Total Equity",      lambda v: f"${v/1e9:.1f}B",  False),
            ("roe_hist",             "Return on Equity",  lambda v: f"{v:.1%}",         True),
            ("operating_cashflow",   "Operating CF",      lambda v: f"${v/1e9:.1f}B",  False),
            ("free_cashflow_hist",   "Free Cash Flow",    lambda v: f"${v/1e9:.1f}B",  False),
        ]

        for key, label, fmt, is_pct in metric_display:
            data = hist.get(key, {})
            if not data:
                continue
            row = {"Metric": label}
            for yr in all_years:
                v = data.get(yr)
                row[yr] = fmt(v) if v is not None else "—"
            row["Change"] = _pct_change(data, all_years)
            summary_rows.append(row)

        st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

        # ── Charts ────────────────────────────────────────────────────────
        st.subheader("Charts")
        c1, c2, c3 = st.columns(3)
        with c1:
            if hist.get("revenue"):
                st.plotly_chart(_bar_chart(hist["revenue"], "Revenue ($B)", billions=True),
                                use_container_width=True)
            if hist.get("eps_hist"):
                st.plotly_chart(_bar_chart(hist["eps_hist"], "EPS – Diluted ($)"),
                                use_container_width=True)
        with c2:
            if hist.get("net_income"):
                st.plotly_chart(_bar_chart(hist["net_income"], "Net Income ($B)", billions=True),
                                use_container_width=True)
            if hist.get("roe_hist"):
                st.plotly_chart(_bar_chart(hist["roe_hist"], "ROE (%)", pct=True),
                                use_container_width=True)
        with c3:
            if hist.get("free_cashflow_hist"):
                st.plotly_chart(_bar_chart(hist["free_cashflow_hist"], "Free Cash Flow ($B)", billions=True),
                                use_container_width=True)
            # Margins line chart
            margin_data = {k: hist[k] for k in
                           ("gross_margin_hist", "operating_margin_hist", "net_margin_hist")
                           if hist.get(k)}
            if margin_data:
                fig_m = go.Figure()
                mlabels = {"gross_margin_hist": "Gross", "operating_margin_hist": "Operating", "net_margin_hist": "Net"}
                mcolors = ["#2ca02c", "#ff7f0e", "#1f77b4"]
                for (k, lbl), col in zip(mlabels.items(), mcolors):
                    d = margin_data.get(k, {})
                    if d:
                        yrs = sorted(d.keys())
                        fig_m.add_trace(go.Scatter(
                            x=yrs, y=[d[y]*100 for y in yrs],
                            mode="lines+markers", name=lbl, line=dict(color=col),
                        ))
                fig_m.update_layout(title="Margins (%)", yaxis_title="%",
                                    template="plotly_white", height=280,
                                    margin=dict(l=0, r=0, t=40, b=20))
                st.plotly_chart(fig_m, use_container_width=True)

        # ── AI Financial Analysis ─────────────────────────────────────────
        st.subheader("AI Financial Trend Analysis")
        st.caption("Powered by AI — analyzing key drivers of change across the 3-year period.")
        report_area = st.empty()
        full_text = ""

        with st.spinner("Analyzing financial trends…"):
            for chunk in analyze_financials_stream(symbol, company_name, sector, hist):
                full_text += chunk
                report_area.markdown(full_text + "▌")

        report_area.markdown(full_text)
        st.success("Analysis complete.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 — Stock News
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📰 Stock News":
    st.title("📰 Stock News")
    st.caption("Recent headlines for a single stock with AI-powered sentiment analysis.")

    symbol = st.text_input("Ticker symbol", key="news_ticker").strip().upper()

    if symbol and st.button("Load News", type="primary"):
        with st.spinner(f"Fetching {symbol}…"):
            try:
                info = fetch_stock(symbol)
                stock_news = fetch_news(symbol)
            except Exception as e:
                st.error(str(e))
                st.stop()

        company_name = info.get("longName", symbol)
        sector       = info.get("sector", "N/A")
        industry     = info.get("industry", "N/A")

        st.subheader(company_name)
        st.caption(f"{sector} · {industry}")
        st.divider()

        if not stock_news:
            st.info("No recent news available. Disable Demo Mode to fetch live headlines.")
        else:
            st.caption(f"{len(stock_news)} recent articles")
            for item in stock_news:
                _render_news_item(item)

            st.subheader("AI News Analysis")
            st.caption("Summarizing key themes and stock impact…")
            news_area = st.empty()
            full_news = ""
            for chunk in analyze_stock_news_stream(symbol, company_name, sector, stock_news):
                full_news += chunk
                news_area.markdown(full_news + "▌")
            news_area.markdown(full_news)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 6 — Industry Analysis
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🏭 Industry":
    st.title("🏭 Industry Analysis")
    st.caption("Competitive intelligence from sector peers with AI-powered macro analysis.")

    symbol = st.text_input("Focus ticker (your stock)", key="ind_ticker").strip().upper()

    custom_peers_raw = st.text_input(
        "Custom peers (optional, comma-separated)",
        placeholder="e.g. MSFT, GOOGL, AMZN — leave empty to auto-detect top 5 sector peers",
        key="ind_custom_peers",
    )

    if symbol and st.button("Load Industry News", type="primary"):
        with st.spinner(f"Fetching {symbol}…"):
            try:
                info = fetch_stock(symbol)
            except Exception as e:
                st.error(str(e))
                st.stop()

        company_name = info.get("longName", symbol)
        sector       = info.get("sector", "N/A")
        industry     = info.get("industry", "N/A")

        st.subheader(company_name)
        st.caption(f"{sector} · {industry}")
        st.divider()

        custom_peers = [p.strip().upper() for p in custom_peers_raw.split(",") if p.strip()]

        with st.spinner("Loading peer news…"):
            if custom_peers:
                industry_news, peers_used = fetch_peers_news_by_list(custom_peers)
                st.caption(f"Using custom peers: **{', '.join(custom_peers)}**")
            else:
                industry_news, peers_used = fetch_sector_peers_news(sector, exclude_symbol=symbol)
                default_peers = SECTOR_PEERS.get(sector, [])
                if default_peers:
                    peer_pool = ", ".join(p for p in default_peers if p.upper() != symbol)
                    st.caption(f"**Auto peer pool ({sector}):** {peer_pool}")

        if not industry_news:
            st.info("No peer news available. Disable Demo Mode or enter custom peer tickers.")
        else:
            if peers_used:
                st.caption(f"Sources: **{', '.join(peers_used)}** · {len(industry_news)} articles")
            for item in industry_news:
                _render_news_item(item)

            st.subheader("AI Industry Analysis")
            st.caption("Analyzing competitive dynamics across sector peers…")
            ind_area = st.empty()
            full_ind = ""
            for chunk in analyze_industry_stream(sector, industry, company_name,
                                                  industry_news, peers=peers_used):
                full_ind += chunk
                ind_area.markdown(full_ind + "▌")
            ind_area.markdown(full_ind)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 7 — Compare
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⚖️ Compare":
    st.title("⚖️ Compare Stocks")

    symbols_raw = st.text_input(
        "Enter 2–4 tickers to compare (comma separated)",
        "AAPL, MSFT, GOOGL",
    )
    symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()][:4]

    if len(symbols) < 2:
        st.info("Enter at least 2 tickers.")
        st.stop()

    if st.button("Compare", type="primary"):
        infos = []
        with st.spinner("Fetching data…"):
            for sym in symbols:
                try:
                    infos.append(fetch_stock(sym))
                except Exception as e:
                    st.warning(f"Skipping {sym}: {e}")

        if len(infos) < 2:
            st.error("Need at least 2 valid symbols.")
            st.stop()

        # Side-by-side metrics table
        st.subheader("Metrics Comparison")
        compare_keys = [
            "current_price", "market_cap", "pe_ratio", "forward_pe",
            "pb_ratio", "roe", "net_margin", "gross_margin",
            "revenue_growth", "debt_to_equity", "current_ratio", "beta",
        ]

        rows = {}
        for info in infos:
            sym = info.get("symbol", "?")
            m = extract_metrics(info)
            rows[sym] = {}
            for k in compare_keys:
                v = m.get(k)
                if v is None:
                    rows[sym][METRIC_LABELS[k]] = "N/A"
                elif k in ("roe", "net_margin", "gross_margin", "revenue_growth"):
                    rows[sym][METRIC_LABELS[k]] = f"{v:.1%}"
                elif k == "market_cap":
                    rows[sym][METRIC_LABELS[k]] = f"${v/1e9:.1f}B"
                else:
                    rows[sym][METRIC_LABELS[k]] = f"{v:.2f}"

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # Price chart overlay
        st.subheader("Price Performance (1 Year, Normalised)")
        fig = go.Figure()
        for info in infos:
            sym = info.get("symbol", "?")
            hist = fetch_price_history(sym, period="1y")
            if not hist.empty:
                normalised = hist["Close"] / hist["Close"].iloc[0] * 100
                fig.add_trace(go.Scatter(
                    x=hist.index, y=normalised,
                    mode="lines", name=sym,
                ))
        fig.update_layout(
            yaxis_title="Indexed Price (base=100)",
            template="plotly_white", height=350,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        # AI comparison
        st.subheader("AI Comparison Report")
        report_area = st.empty()
        full_text = ""

        with st.spinner("Claude is comparing…"):
            for chunk in compare_stocks_stream(infos):
                full_text += chunk
                report_area.markdown(full_text + "▌")

        report_area.markdown(full_text)
        st.success("Comparison complete.")

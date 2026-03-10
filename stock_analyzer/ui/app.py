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

from stock_analyzer.data.db import init_db
from stock_analyzer.data.ingestion.yfinance_client import (
    fetch_stock, fetch_price_history
)
from stock_analyzer.analysis.fundamental import (
    extract_metrics, score_health, METRIC_LABELS
)
from stock_analyzer.analysis.screener import ScreenerCriteria, screen
from stock_analyzer.analysis.ai import analyze_stock_stream, compare_stocks_stream

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
st.set_page_config(page_title="Stock Analyzer", page_icon="📈", layout="wide")

# ── Sidebar navigation ────────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigation",
    ["📊 Stock Overview", "🔍 Screener", "🤖 AI Analysis", "⚖️ Compare"],
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
    st.caption("Powered by Claude (claude-opus-4-6) with extended thinking.")

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
# PAGE 4 — Compare
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

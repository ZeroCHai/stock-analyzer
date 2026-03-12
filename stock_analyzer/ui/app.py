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
from plotly.subplots import make_subplots
from datetime import datetime

from stock_analyzer.data.db import init_db
from stock_analyzer.data.ingestion.yfinance_client import (
    fetch_stock, fetch_price_history, set_demo_mode, is_demo_mode,
    fetch_income_statement, fetch_balance_sheet, fetch_cash_flow,
    fetch_news, SECTOR_ETF, MARKET_INDICES,
    fetch_sector_performance, fetch_sector_details, fetch_prediction_markets,
    fetch_market_indices,
)
from stock_analyzer.data.ingestion.demo_data import DEMO_STOCKS
from stock_analyzer.analysis.fundamental import (
    extract_metrics, score_health, METRIC_LABELS, extract_historical_metrics,
)
from stock_analyzer.analysis.screener import ScreenerCriteria, screen

# ── Helpers ───────────────────────────────────────────────────────────────────
def _render_news_item(item: dict):
    """Render one Yahoo Finance news item as a styled .nc card."""
    title     = item.get("title", "Untitled")
    link      = item.get("link", "")
    publisher = item.get("publisher", "")
    ts        = item.get("providerPublishTime", 0)
    date_str  = datetime.fromtimestamp(ts).strftime("%b %d, %Y") if ts else ""
    tickers   = item.get("relatedTickers", [])

    title_html = (f'<a href="{link}" target="_blank" rel="noopener" class="nc-title">{title}</a>'
                  if link else f'<span class="nc-title">{title}</span>')
    tags_html  = "".join(f'<span class="nc-tag">{t}</span>' for t in tickers[:5])
    meta_parts = [p for p in [publisher, date_str] if p]
    meta_html  = " · ".join(meta_parts) + (f"&nbsp;{tags_html}" if tags_html else "")
    st.markdown(
        f'<div class="nc">{title_html}<div class="nc-meta">{meta_html}</div></div>',
        unsafe_allow_html=True,
    )


def _chart_defaults(height: int = 320) -> dict:
    """Common dark-theme layout kwargs for all Plotly charts."""
    return dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,20,32,0.6)",
        font=dict(family="'IBM Plex Mono', monospace", size=11, color="#DDE6ED"),
        height=height,
        margin=dict(l=0, r=0, t=40, b=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    )


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
    colors = ["#FF3350" if v < 0 else "#00C805" for v in vals]
    fig = go.Figure(go.Bar(
        x=years, y=vals, marker_color=colors,
        text=[f"{v:.1f}" for v in vals], textposition="outside",
        textfont=dict(family="'IBM Plex Mono', monospace", size=11),
    ))
    fig.update_layout(
        title=title, yaxis_title=ylabel,
        **_chart_defaults(height=280),
    )
    return fig


# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
st.set_page_config(page_title="Stock Analyzer", page_icon="📈", layout="wide")

# ── Design system: Financial Terminal Dark ────────────────────────────────────
# Aesthetic direction (frontend-design skill):
#   "Trading Terminal" — obsidian surfaces, IBM Plex Mono for all numbers,
#   Syne display headers, electric-green (#00C805) accent, strict data hierarchy.
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ── CSS variables ── */
:root {
    --bg:       #080C12;
    --surface:  #0E1420;
    --border:   #1A2535;
    --green:    #00C805;
    --red:      #FF3350;
    --blue:     #4C9EFF;
    --text:     #DDE6ED;
    --muted:    #4A6070;
    --mono:     'IBM Plex Mono', monospace;
    --display:  'Syne', sans-serif;
    --body:     'DM Sans', sans-serif;
}

/* ── Global typography ── */
html, body, [class*="css"], p, li, span, div { font-family: var(--body) !important; }
h1 { font-family: var(--display) !important; font-weight: 800 !important;
     font-size: 1.9rem !important; letter-spacing: -0.03em !important;
     color: var(--text) !important; margin-bottom: 0.1rem !important; }
h2 { font-family: var(--display) !important; font-weight: 700 !important;
     font-size: 1.1rem !important; letter-spacing: -0.01em !important; }
h3 { font-family: var(--display) !important; font-weight: 700 !important;
     font-size: 0.95rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: var(--green);
    color: #000;
    font-weight: 700;
    font-size: 0.875rem;
    letter-spacing: 0.03em;
    border: none;
    border-radius: 6px;
    padding: 0.55rem 2rem;
    transition: all 0.15s ease;
    box-shadow: 0 0 0 rgba(0,200,5,0);
    position: relative;
}
.stButton > button:hover {
    background: #00E306;
    color: #000;
    box-shadow: 0 0 18px rgba(0,200,5,0.35);
    transform: translateY(-1px);
}
.stButton > button:active { background: #009A03; transform: translateY(0); }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.9rem 1.1rem !important;
    position: relative;
    overflow: hidden;
}
[data-testid="stMetric"]::after {
    content: '';
    position: absolute;
    inset: 0 0 auto 0;
    height: 2px;
    background: linear-gradient(90deg, var(--green) 0%, transparent 60%);
}
[data-testid="stMetricLabel"] {
    font-size: 0.62rem !important;
    color: var(--muted) !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    font-family: var(--mono) !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
}
[data-testid="stMetricDelta"] { font-family: var(--mono) !important; font-size: 0.78rem !important; }

/* ── Dividers ── */
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1rem 0 !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border);
    gap: 0;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-weight: 700;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.65rem 1.2rem;
    color: var(--muted);
    border-radius: 0;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: color 0.15s;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--green) !important;
    border-bottom-color: var(--green) !important;
    background: transparent !important;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; border: 1px solid var(--border) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: #050810 !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] .stRadio label {
    font-family: var(--body) !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: var(--muted) !important;
    padding: 0.2rem 0;
    transition: color 0.12s;
}
[data-testid="stSidebar"] .stRadio label:hover { color: var(--green) !important; }
[data-testid="stSidebar"] .stRadio > label {
    font-size: 0.6rem !important;
    font-weight: 700 !important;
    color: #1E2F3E !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: var(--mono) !important;
    font-size: 0.875rem !important;
    transition: border-color 0.15s, box-shadow 0.15s;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 3px rgba(0,200,5,0.1) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] { border: 1px solid var(--border) !important; border-radius: 10px !important; overflow: hidden; }
[data-testid="stExpander"] summary { font-weight: 600; font-size: 0.88rem; }

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 8px; font-size: 0.875rem; }

/* ── Caption ── */
[data-testid="stCaptionContainer"] { color: var(--muted) !important; font-size: 0.8rem !important; }

/* ── News card ── */
.nc {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--green);
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.nc:hover { border-color: #2A3F50; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
.nc-title { font-weight: 600; font-size: 0.9rem; line-height: 1.45;
            color: var(--text); margin-bottom: 0.3rem; display: block; }
.nc-title a { color: var(--text); text-decoration: none; }
.nc-title a:hover { color: var(--green); }
.nc-meta { font-size: 0.73rem; color: var(--muted); display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }
.nc-tag { display: inline-block; background: rgba(0,200,5,0.08); color: var(--green);
          border: 1px solid rgba(0,200,5,0.2); border-radius: 3px; padding: 1px 5px;
          font-size: 0.66rem; font-weight: 700; font-family: var(--mono); letter-spacing: 0.02em; }

/* ── Company header ── */
.co-sym  { font-family: var(--mono); font-size: 0.68rem; font-weight: 600; color: var(--green);
           letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.2rem; }
.co-name { font-family: var(--display); font-size: 1.6rem; font-weight: 800;
           letter-spacing: -0.025em; line-height: 1.15; margin-bottom: 0.3rem; }
.co-meta { font-size: 0.78rem; color: var(--muted); }

/* ── Section label ── */
.sec-lbl { font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em;
           color: var(--muted); padding-bottom: 0.5rem; border-bottom: 1px solid var(--border);
           margin-bottom: 0.75rem; }

/* ── PDF button ── */
.pdf-btn {
    position: fixed; top: 14px; right: 16px; z-index: 9999;
    background: rgba(0,200,5,0.1); color: var(--green);
    font-weight: 700; font-size: 0.72rem; letter-spacing: 0.05em;
    border: 1px solid rgba(0,200,5,0.25); border-radius: 20px;
    padding: 0.32rem 0.9rem; cursor: pointer; backdrop-filter: blur(8px);
    transition: all 0.15s ease;
}
.pdf-btn:hover { background: rgba(0,200,5,0.2); box-shadow: 0 0 14px rgba(0,200,5,0.25); }

/* ── Print ── */
@media print {
    .pdf-btn, [data-testid="stSidebar"], [data-testid="stToolbar"],
    header, footer, .stDeployButton, [data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding: 1rem !important; max-width: 100% !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<button class="pdf-btn" onclick="window.print()">⬇ Save as PDF</button>',
    unsafe_allow_html=True,
)

# ── Sidebar header ────────────────────────────────────────────────────────────
_logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
_logo_col, _title_col = st.sidebar.columns([1, 2.6], gap="small")
with _logo_col:
    st.image(_logo_path, width=64)
with _title_col:
    st.markdown(
        "<div style='padding-top:6px'>"
        "<span style='font-size:1.25rem;font-weight:800;letter-spacing:-0.01em;"
        "line-height:1.15'>Stock<br>Analyzer</span></div>",
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
    ["🌍 Global Markets", "📊 Stock Overview", "🔍 Screener", "📑 Financial Analysis",
     "📰 Stock News", "🏭 Sector Markets", "⚖️ Compare", "📈 Technical Analysis",
     "🎯 Prediction Markets"],
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 0 — Global Markets (home page)
# ─────────────────────────────────────────────────────────────────────────────
if page == "🌍 Global Markets":
    st.title("🌍 Global Markets")
    st.caption("Real-time performance of major indices, commodities, and volatility — powered by Yahoo Finance.")

    if is_demo_mode():
        st.info("Live market data requires a network connection. Disable Demo Mode to load global indices.")
    else:
        with st.spinner("Loading market indices…"):
            indices = fetch_market_indices()

        if not indices:
            st.warning("Could not load market data. Check your network connection.")
        else:
            regions_order = ["Americas", "Europe", "Asia-Pacific", "Commodities", "Volatility"]
            by_region: dict[str, list] = {}
            for idx in indices:
                by_region.setdefault(idx["region"], []).append(idx)

            def _chg_html(v) -> str:
                if v is None:
                    return '<span style="color:var(--muted)">—</span>'
                color = "var(--green)" if v >= 0 else "var(--red)"
                arrow = "▲" if v >= 0 else "▼"
                return f'<span style="color:{color};font-family:var(--mono);font-size:0.82rem">{arrow} {abs(v)*100:.2f}%</span>'

            def _price_fmt(v) -> str:
                if v >= 1000:
                    return f"{v:,.0f}"
                elif v >= 10:
                    return f"{v:,.2f}"
                return f"{v:.4f}"

            for region in regions_order:
                items = by_region.get(region)
                if not items:
                    continue
                st.markdown(
                    f'<div style="font-size:0.6rem;font-weight:700;text-transform:uppercase;'
                    f'letter-spacing:0.1em;color:var(--muted);margin:1rem 0 0.45rem">— {region} —</div>',
                    unsafe_allow_html=True,
                )
                cols = st.columns(len(items))
                for col, item in zip(cols, items):
                    with col:
                        chg_1d = item.get("chg_1d")
                        border_color = "var(--green)" if (chg_1d or 0) >= 0 else "var(--red)"
                        st.markdown(
                            f'<div style="background:var(--surface);border:1px solid var(--border);'
                            f'border-top:2px solid {border_color};border-radius:8px;'
                            f'padding:0.7rem 0.85rem;margin-bottom:0.3rem">'
                            f'<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;'
                            f'text-transform:uppercase;color:var(--muted);margin-bottom:0.2rem">'
                            f'{item["name"]}</div>'
                            f'<div style="font-family:var(--mono);font-weight:600;font-size:1.05rem;'
                            f'margin-bottom:0.25rem">{_price_fmt(item["price"])}</div>'
                            f'<div style="display:flex;gap:0.6rem;flex-wrap:wrap">'
                            f'<span style="font-size:0.68rem;color:var(--muted)">1D&nbsp;{_chg_html(chg_1d)}</span>'
                            f'<span style="font-size:0.68rem;color:var(--muted)">1W&nbsp;{_chg_html(item.get("chg_1w"))}</span>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

            # 1-Day performance chart (all except Volatility)
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            chart_items = [i for i in indices
                           if i.get("chg_1d") is not None and i["region"] != "Volatility"]
            if chart_items:
                sorted_items = sorted(chart_items, key=lambda x: x["chg_1d"])
                vals   = [i["chg_1d"] * 100 for i in sorted_items]
                colors = ["#00C805" if v >= 0 else "#FF3350" for v in vals]
                fig_idx = go.Figure(go.Bar(
                    x=vals, y=[i["name"] for i in sorted_items], orientation="h",
                    marker_color=colors,
                    text=[f"{v:+.2f}%" for v in vals],
                    textposition="outside",
                    textfont=dict(family="'IBM Plex Mono', monospace", size=10),
                ))
                layout_idx = _chart_defaults(height=max(280, len(sorted_items) * 30))
                layout_idx["margin"] = dict(l=0, r=70, t=36, b=10)
                fig_idx.update_layout(title="1-Day Performance (%)", xaxis_title="%", **layout_idx)
                st.plotly_chart(fig_idx, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — Stock Overview
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📊 Stock Overview":
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
            sector_str   = info.get("sector", "")
            industry_str = info.get("industry", "")
            meta_parts   = [p for p in [sector_str, industry_str] if p]
            st.markdown(
                f'<div class="co-sym">{symbol}</div>'
                f'<div class="co-name">{info.get("longName", symbol)}</div>'
                f'<div class="co-meta">{" · ".join(meta_parts)}</div>',
                unsafe_allow_html=True,
            )
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
                    colors_m = ["#00C805", "#4C9EFF", "#FF3350"]
                    for (key, label), color in zip(margin_labels.items(), colors_m):
                        d = hist.get(key, {})
                        if d:
                            yrs = sorted(d.keys())
                            fig_m.add_trace(go.Scatter(
                                x=yrs, y=[d[y] * 100 for y in yrs],
                                mode="lines+markers", name=label,
                                line=dict(color=color, width=2),
                                marker=dict(size=6),
                            ))
                    fig_m.update_layout(
                        title="Margin Trends (%)", yaxis_title="%",
                        **_chart_defaults(height=280),
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
                line=dict(color="#00C805", width=2),
                fill="tozeroy",
                fillcolor="rgba(0,200,5,0.06)",
            ))
            layout = _chart_defaults(height=350)
            layout["margin"] = dict(l=0, r=0, t=20, b=0)
            fig.update_layout(xaxis_title="Date", yaxis_title="Price (USD)", **layout)
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
# PAGE 3 — Financial Analysis
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📑 Financial Analysis":
    st.title("📑 Financial Analysis")
    st.caption("3-year financial statements for a single stock.")

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
        sector_str   = info.get("sector", "")
        industry_str = info.get("industry", "")
        meta_parts   = [p for p in [sector_str, industry_str] if p]
        st.markdown(
            f'<div class="co-sym">{symbol}</div>'
            f'<div class="co-name">{company_name}</div>'
            f'<div class="co-meta">{" · ".join(meta_parts)}</div>',
            unsafe_allow_html=True,
        )

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
                mcolors = ["#00C805", "#4C9EFF", "#FF3350"]
                for (k, lbl), col in zip(mlabels.items(), mcolors):
                    d = margin_data.get(k, {})
                    if d:
                        yrs = sorted(d.keys())
                        fig_m.add_trace(go.Scatter(
                            x=yrs, y=[d[y]*100 for y in yrs],
                            mode="lines+markers", name=lbl,
                            line=dict(color=col, width=2), marker=dict(size=6),
                        ))
                fig_m.update_layout(title="Margins (%)", yaxis_title="%",
                                    **_chart_defaults(height=280))
                st.plotly_chart(fig_m, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 — Stock News
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📰 Stock News":
    st.title("📰 Stock News")
    st.caption("Recent headlines for a single stock.")

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
        sector_str   = info.get("sector", "")
        industry_str = info.get("industry", "")
        meta_parts   = [p for p in [sector_str, industry_str] if p]
        st.markdown(
            f'<div class="co-sym">{symbol}</div>'
            f'<div class="co-name">{company_name}</div>'
            f'<div class="co-meta">{" · ".join(meta_parts)}</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        if not stock_news:
            st.info("No recent news available. Disable Demo Mode to fetch live headlines.")
        else:
            st.caption(f"{len(stock_news)} recent articles")
            for item in stock_news:
                _render_news_item(item)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 — Sector Markets
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🏭 Sector Markets":
    st.title("🏭 Sector Markets")
    st.caption("US equity sector performance and top companies — powered by Yahoo Finance.")

    tab_perf, tab_detail = st.tabs(["Sector Performance", "Sector Detail"])

    with tab_perf:
        if is_demo_mode():
            st.info("Sector performance requires a live connection. Disable Demo Mode to load.")
        else:
            with st.spinner("Loading sector data…"):
                sector_data = fetch_sector_performance()

            if not sector_data:
                st.error("Could not load sector performance. Check your network connection.")
            else:
                df_s = pd.DataFrame(sector_data)

                # Performance bar chart
                bar_colors = ["#00C805" if (v or 0) >= 0 else "#FF3B3B" for v in df_s["1D %"]]
                fig_sec = go.Figure(go.Bar(
                    x=df_s["Sector"],
                    y=[(v * 100 if v is not None else 0) for v in df_s["1D %"]],
                    marker_color=bar_colors,
                    text=[f"{v*100:+.2f}%" if v is not None else "N/A" for v in df_s["1D %"]],
                    textposition="outside",
                ))
                layout_sec = _chart_defaults(height=420)
                layout_sec["margin"] = dict(l=0, r=0, t=40, b=110)
                layout_sec["xaxis_tickangle"] = -30
                fig_sec.update_layout(
                    title="Sector 1-Day Performance (%)",
                    yaxis_title="Change (%)",
                    **layout_sec,
                )
                st.plotly_chart(fig_sec, use_container_width=True)

                # Performance table
                st.subheader("Performance Summary")
                disp = df_s.copy()
                disp["Price"] = disp["Price"].apply(lambda v: f"${v:.2f}" if v is not None else "N/A")
                for col in ("1D %", "1W %", "1M %"):
                    disp[col] = disp[col].apply(
                        lambda v: f"{v*100:+.2f}%" if v is not None else "N/A"
                    )
                st.dataframe(disp, hide_index=True, use_container_width=True)

    with tab_detail:
        selected_sector = st.selectbox("Select a sector", list(SECTOR_ETF.keys()),
                                       key="sector_detail_sel")
        if st.button("Load Sector Detail", key="sector_detail_btn"):
            if is_demo_mode():
                st.info("Sector detail requires a live connection. Disable Demo Mode.")
            else:
                with st.spinner(f"Loading {selected_sector}…"):
                    detail = fetch_sector_details(selected_sector)

                if not detail:
                    st.warning("Could not load sector details.")
                else:
                    st.caption(f"Benchmark ETF: **{SECTOR_ETF.get(selected_sector, '')}**")

                    top_co = detail.get("top_companies")
                    if top_co is not None and not top_co.empty:
                        st.subheader("Top Companies")
                        st.dataframe(top_co, use_container_width=True)

                    industries = detail.get("industries")
                    if industries is not None and not industries.empty:
                        st.subheader("Sub-Industries")
                        st.dataframe(industries, use_container_width=True)


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
        layout_cmp = _chart_defaults(height=350)
        layout_cmp["margin"] = dict(l=0, r=0, t=20, b=0)
        fig.update_layout(yaxis_title="Indexed Price (base=100)", **layout_cmp)
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 8 — Technical Analysis
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📈 Technical Analysis":
    st.title("📈 Technical Analysis")
    st.caption("K-line · Volume · MA · Bollinger Bands · RSI · MACD")

    symbol = st.text_input("Ticker symbol", key="ta_ticker").strip().upper()
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=3, key="ta_period")

    if symbol and st.button("Analyze", type="primary", key="ta_btn"):
        with st.spinner(f"Loading {symbol}…"):
            try:
                info = fetch_stock(symbol)
                df   = fetch_price_history(symbol, period=period)
            except Exception as e:
                st.error(str(e))
                st.stop()

        if df.empty:
            st.error("No price data available.")
            st.stop()

        company_name = info.get("longName", symbol)
        sector_str   = info.get("sector", "")
        industry_str = info.get("industry", "")
        meta_parts   = [p for p in [sector_str, industry_str] if p]
        st.markdown(
            f'<div class="co-sym">{symbol}</div>'
            f'<div class="co-name">{company_name}</div>'
            f'<div class="co-meta">{" · ".join(meta_parts)}</div>',
            unsafe_allow_html=True,
        )

        # ── Compute indicators ─────────────────────────────────────────────
        df = df.copy()
        df["MA20"]  = df["Close"].rolling(20).mean()
        df["MA50"]  = df["Close"].rolling(50).mean()
        df["MA200"] = df["Close"].rolling(200).mean()

        df["BB_mid"]   = df["Close"].rolling(20).mean()
        df["BB_std"]   = df["Close"].rolling(20).std()
        df["BB_upper"] = df["BB_mid"] + 2 * df["BB_std"]
        df["BB_lower"] = df["BB_mid"] - 2 * df["BB_std"]

        delta    = df["Close"].diff()
        gain     = delta.clip(lower=0)
        loss     = (-delta).clip(lower=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs       = avg_gain / avg_loss.replace(0, float("nan"))
        df["RSI"] = 100 - (100 / (1 + rs))

        ema12         = df["Close"].ewm(span=12, adjust=False).mean()
        ema26         = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"]    = ema12 - ema26
        df["Signal"]  = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_hist"] = df["MACD"] - df["Signal"]

        last  = df.iloc[-1]
        price = last["Close"]

        # ── Summary metrics row ────────────────────────────────────────────
        rsi_val  = last["RSI"]
        macd_val = last["MACD"]
        sig_val  = last["Signal"]
        ma20_val = last["MA20"]
        ma50_val = last["MA50"]

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Price", f"${price:.2f}")
        with col2:
            if pd.notna(ma20_val):
                d = (price - ma20_val) / ma20_val
                st.metric("vs MA20", f"${ma20_val:.2f}", f"{d:+.1%}")
        with col3:
            if pd.notna(ma50_val):
                d = (price - ma50_val) / ma50_val
                st.metric("vs MA50", f"${ma50_val:.2f}", f"{d:+.1%}")
        with col4:
            if pd.notna(rsi_val):
                lbl = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
                st.metric("RSI(14)", f"{rsi_val:.1f}", lbl)
        with col5:
            if pd.notna(macd_val) and pd.notna(sig_val):
                cross = "Bullish" if macd_val > sig_val else "Bearish"
                st.metric("MACD Signal", f"{macd_val:.3f}", cross)

        st.divider()

        # ── Charts ─────────────────────────────────────────────────────────
        tab1, tab2, tab3 = st.tabs(["K线 + MA + 布林带", "RSI", "MACD"])

        with tab1:
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.75, 0.25],
                vertical_spacing=0.03,
            )
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"],
                name="OHLC",
                increasing_line_color="#00C805",
                decreasing_line_color="#FF3B3B",
            ), row=1, col=1)

            # Bollinger Bands
            fig.add_trace(go.Scatter(
                x=df.index, y=df["BB_upper"], name="BB Upper",
                line=dict(color="#aaaaaa", width=1, dash="dot"),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df["BB_lower"], name="BB Lower",
                line=dict(color="#aaaaaa", width=1, dash="dot"),
                fill="tonexty", fillcolor="rgba(150,150,150,0.08)",
            ), row=1, col=1)

            # Moving averages
            for ma_col, color in [("MA20", "#f5a623"), ("MA50", "#4a90d9"), ("MA200", "#9b59b6")]:
                if df[ma_col].notna().any():
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df[ma_col], name=ma_col,
                        line=dict(color=color, width=1.5),
                    ), row=1, col=1)

            # Volume bars
            vol_colors = [
                "#00C805" if c >= o else "#FF3B3B"
                for c, o in zip(df["Close"], df["Open"])
            ]
            fig.add_trace(go.Bar(
                x=df.index, y=df["Volume"], name="Volume",
                marker_color=vol_colors, showlegend=False,
            ), row=2, col=1)

            layout_ta = _chart_defaults(height=620)
            layout_ta["margin"] = dict(l=0, r=0, t=30, b=0)
            layout_ta["legend"] = dict(orientation="h", yanchor="bottom", y=1.01, x=0,
                                       bgcolor="rgba(0,0,0,0)", borderwidth=0)
            fig.update_layout(xaxis_rangeslider_visible=False, **layout_ta)
            fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(
                x=df.index, y=df["RSI"], name="RSI(14)",
                line=dict(color="#4a90d9", width=2),
            ))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red",
                               annotation_text="超买 70", annotation_position="right")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green",
                               annotation_text="超卖 30", annotation_position="right")
            fig_rsi.add_hline(y=50, line_dash="dot", line_color="#999999")
            layout_rsi = _chart_defaults(height=350)
            layout_rsi["margin"] = dict(l=0, r=0, t=40, b=0)
            fig_rsi.update_layout(title="RSI (14)", yaxis_title="RSI",
                                  yaxis_range=[0, 100], **layout_rsi)
            st.plotly_chart(fig_rsi, use_container_width=True)

        with tab3:
            fig_macd = go.Figure()
            hist_colors = [
                "#00C805" if v >= 0 else "#FF3B3B"
                for v in df["MACD_hist"].fillna(0)
            ]
            fig_macd.add_trace(go.Bar(
                x=df.index, y=df["MACD_hist"], name="Histogram",
                marker_color=hist_colors,
            ))
            fig_macd.add_trace(go.Scatter(
                x=df.index, y=df["MACD"], name="MACD",
                line=dict(color="#4a90d9", width=2),
            ))
            fig_macd.add_trace(go.Scatter(
                x=df.index, y=df["Signal"], name="Signal",
                line=dict(color="#f5a623", width=1.5),
            ))
            layout_macd = _chart_defaults(height=350)
            layout_macd["margin"] = dict(l=0, r=0, t=40, b=0)
            fig_macd.update_layout(title="MACD (12, 26, 9)", yaxis_title="Value",
                                   **layout_macd)
            st.plotly_chart(fig_macd, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 8 — Prediction Markets
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🎯 Prediction Markets":
    st.title("🎯 Prediction Markets")
    st.caption("Live prediction markets — sourced from Yahoo Finance.")

    if is_demo_mode():
        st.info("Prediction Markets requires a live connection. Disable Demo Mode to load.")
    else:
        with st.spinner("Fetching prediction markets from Yahoo Finance…"):
            markets = fetch_prediction_markets()

        if not markets:
            st.info(
                "Prediction market data could not be loaded automatically. "
                "View them directly on Yahoo Finance:"
            )
            st.link_button(
                "Open Yahoo Finance Prediction Markets",
                "https://finance.yahoo.com/markets/prediction-markets/",
            )
        else:
            st.success(f"{len(markets)} active markets loaded.")

            rows = []
            for q in markets:
                price_raw = q.get("regularMarketPrice")
                price     = price_raw.get("fmt") if isinstance(price_raw, dict) else price_raw

                chg_raw   = q.get("regularMarketChangePercent")
                chg       = chg_raw.get("fmt") if isinstance(chg_raw, dict) else (
                    f"{chg_raw:+.2f}%" if isinstance(chg_raw, (int, float)) else chg_raw
                )

                vol_raw   = q.get("regularMarketVolume")
                vol       = vol_raw.get("fmt") if isinstance(vol_raw, dict) else vol_raw

                rows.append({
                    "Symbol":   q.get("symbol", ""),
                    "Name":     q.get("shortName") or q.get("longName") or q.get("displayName", ""),
                    "Price":    price,
                    "Change":   chg,
                    "Volume":   vol,
                })

            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            st.link_button(
                "View on Yahoo Finance",
                "https://finance.yahoo.com/markets/prediction-markets/",
            )

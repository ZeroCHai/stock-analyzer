"""
AI-powered fundamental analysis.

Supports three authentication modes (auto-detected from environment):
  1. Gemini API key          — set GEMINI_API_KEY
  2. Gemini Vertex AI OAuth  — set GOOGLE_CLOUD_PROJECT (uses ADC / service account)
  3. ByteDance Ark AK/SK     — set AI_PROVIDER=ark, VOLC_ACCESSKEY, VOLC_SECRETKEY, ARK_MODEL
"""

from __future__ import annotations
import time
from openai import OpenAI
from stock_analyzer.config import (
    AI_PROVIDER,
    ARK_API_KEY, ARK_BASE_URL, ARK_EP_MODEL, VOLC_AK, VOLC_SK,
    GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, GCP_PROJECT, GCP_LOCATION,
)
from stock_analyzer.analysis.fundamental import extract_metrics, METRIC_LABELS

_client = None
_oauth_expires_at: float = 0.0


def _make_vertex_client() -> tuple:
    """Create an OpenAI client pointed at Vertex AI using ADC, plus its expiry time."""
    import google.auth
    import google.auth.transport.requests

    creds, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    proj = GCP_PROJECT or project
    base_url = (
        f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{proj}/locations/{GCP_LOCATION}/endpoints/openapi/"
    )
    return OpenAI(api_key=creds.token, base_url=base_url), time.time() + 3600


def _patch_ark_send(client) -> None:
    """
    Monkeypatch the internal httpx.Client.send on an Ark SDK client so that
    openai 2.x fields (store, stream_options, service_tier) are stripped from
    the request body before the bytes hit the network.

    This runs AFTER auth headers are injected by the Ark SDK, so auth is
    unaffected.  ARK uses Bearer-token auth (not body-signing), so modifying
    the body after the auth header is added is safe.
    """
    import httpx as _httpx
    import json as _json

    _STRIP = frozenset(["store", "stream_options", "service_tier"])
    _orig = client._client.send  # openai SyncAPIClient stores httpx as _client

    def _send(request: _httpx.Request, **kwargs):
        try:
            body = _json.loads(request.content)
            if any(f in body for f in _STRIP):
                for f in _STRIP:
                    body.pop(f, None)
                new_bytes = _json.dumps(body).encode()
                # Rebuild request preserving all existing headers (incl. auth)
                hdrs = [(k, v) for k, v in request.headers.items()
                        if k.lower() != "content-length"]
                hdrs.append(("content-length", str(len(new_bytes))))
                request = _httpx.Request(
                    method=request.method,
                    url=str(request.url),
                    headers=hdrs,
                    content=new_bytes,
                )
        except Exception:
            pass
        return _orig(request, **kwargs)

    client._client.send = _send


def _ark_direct_stream(model: str, messages: list, max_tokens: int):
    """
    Call the ARK API directly via requests, completely bypassing the openai SDK.
    This avoids the openai 2.x SDK injecting fields (store, stream_options,
    service_tier) that ARK rejects with HTTP 400.
    """
    import requests
    import json as _json

    url = f"{ARK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }

    with requests.post(url, headers=headers, json=payload, stream=True, timeout=180) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            try:
                chunk = _json.loads(data)
                content = chunk["choices"][0]["delta"].get("content")
                if content:
                    yield content
            except (KeyError, IndexError, _json.JSONDecodeError):
                pass


def _get_client():
    """
    Return the appropriate AI client based on AI_PROVIDER.

    Ark  (default): AK/SK → volcenginesdkarkruntime Ark client
                    API key → None (direct HTTP via _ark_direct_stream)
    Gemini:         Vertex AI OAuth → API key
    """
    global _client, _oauth_expires_at

    if AI_PROVIDER == "ark":
        # Prefer ARK_API_KEY: use direct HTTP, bypassing openai SDK entirely.
        if ARK_API_KEY:
            return None
        # Fallback: AK/SK via volcenginesdkarkruntime, with send-level patch
        # to strip openai 2.x fields (store, stream_options, service_tier).
        if VOLC_AK and VOLC_SK:
            if _client is None:
                from volcenginesdkarkruntime import Ark
                _client = Ark(ak=VOLC_AK, sk=VOLC_SK)
                _patch_ark_send(_client)
            return _client
        return None  # misconfigured — will raise in _effective_model()

    # Gemini — Vertex AI OAuth
    if GCP_PROJECT:
        if time.time() >= _oauth_expires_at - 300:
            _client, _oauth_expires_at = _make_vertex_client()
        return _client

    # Gemini — API key
    if _client is None:
        _client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
    return _client


def _effective_model() -> str:
    """Return the model/endpoint name for the active provider."""
    if AI_PROVIDER == "ark":
        if not ARK_EP_MODEL:
            raise ValueError(
                "ARK_MODEL is not configured. "
                "Set ARK_MODEL=ep-XXXXXXXX-xxxxxx in your .env file."
            )
        return ARK_EP_MODEL
    if GCP_PROJECT:
        return GEMINI_MODEL if GEMINI_MODEL.startswith("google/") else f"google/{GEMINI_MODEL}"
    return GEMINI_MODEL


def _format_metrics(info: dict) -> str:
    metrics = extract_metrics(info)
    lines = [
        f"Company:  {info.get('longName', 'N/A')}",
        f"Ticker:   {info.get('symbol', 'N/A')}",
        f"Sector:   {info.get('sector', 'N/A')}",
        f"Industry: {info.get('industry', 'N/A')}",
        "",
        "--- Key Metrics ---",
    ]
    for key, label in METRIC_LABELS.items():
        v = metrics.get(key)
        if v is None:
            continue
        if key in ("gross_margin", "operating_margin", "net_margin",
                   "roe", "roa", "revenue_growth", "earnings_growth",
                   "dividend_yield", "payout_ratio"):
            lines.append(f"{label}: {v:.1%}")
        elif key == "market_cap":
            lines.append(f"{label}: ${v/1e9:.2f}B")
        elif key == "free_cashflow":
            lines.append(f"{label}: ${v/1e9:.2f}B")
        else:
            lines.append(f"{label}: {v:.2f}")

    description = info.get("longBusinessSummary", "")
    if description:
        lines += ["", "--- Business Description ---", description[:1000]]

    return "\n".join(lines)


def _chat_stream(client, model: str, messages: list, max_tokens: int = 4096):
    """
    Yield text chunks from a chat completion.

    For ARK with API-key auth, client is None and we call _ark_direct_stream()
    directly via requests, bypassing the openai SDK entirely (which in 2.x
    injects fields like store/stream_options/service_tier that ARK rejects).
    """
    if client is None:
        # ARK API-key path: direct HTTP
        yield from _ark_direct_stream(model, messages, max_tokens)
        return

    stream = client.chat.completions.create(
        model=model, max_tokens=max_tokens, stream=True, messages=messages,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


SYSTEM_PROMPT = """You are a senior equity analyst specialising in US stocks.
You combine quantitative rigor with clear, direct communication.
When given fundamental data, you:
1. Identify the company's key competitive advantages (or lack thereof)
2. Assess valuation — is it cheap, fair, or expensive vs. peers and history?
3. Flag red flags in the balance sheet, margins, or growth trends
4. Give an overall investment thesis in plain language
Respond in structured Markdown with clear sections."""


def analyze_stock_stream(info: dict):
    """
    Generator that yields text chunks from Seed2.0's streaming response.
    """
    client = _get_client()
    prompt = _format_metrics(info)

    yield from _chat_stream(client, _effective_model(), max_tokens=4096, messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Please provide a comprehensive fundamental analysis "
                "of the following stock:\n\n" + prompt
            ),
        },
    ])


def analyze_financials_stream(symbol: str, company_name: str, sector: str, hist: dict):
    """
    Stream AI analysis of 3-year financial trends.
    hist: output of extract_historical_metrics()
    """
    client = _get_client()

    def B(v): return f"${v/1e9:.2f}B"
    def P(v): return f"{v:.1%}"
    def D(v): return f"${v:.2f}"

    lines = [
        f"Company: {company_name} ({symbol})",
        f"Sector: {sector}",
        "",
        "3-Year Financial Data (oldest → newest):",
    ]

    metric_defs = [
        ("revenue",              "Revenue",             B),
        ("gross_profit",         "Gross Profit",        B),
        ("gross_margin_hist",    "Gross Margin",        P),
        ("operating_income",     "Operating Income",    B),
        ("operating_margin_hist","Operating Margin",    P),
        ("net_income",           "Net Income",          B),
        ("net_margin_hist",      "Net Margin",          P),
        ("ebitda",               "EBITDA",              B),
        ("eps_hist",             "EPS (Diluted)",       D),
        ("total_assets",         "Total Assets",        B),
        ("total_debt",           "Total Debt",          B),
        ("total_equity",         "Total Equity",        B),
        ("roe_hist",             "Return on Equity",    P),
        ("operating_cashflow",   "Operating Cash Flow", B),
        ("free_cashflow_hist",   "Free Cash Flow",      B),
    ]

    for key, label, fmt in metric_defs:
        data = hist.get(key, {})
        if data:
            years = sorted(data.keys())
            values = " → ".join(f"{y}: {fmt(data[y])}" for y in years)
            lines.append(f"  {label}: {values}")

    prompt = "\n".join(lines)

    yield from _chat_stream(client, _effective_model(), max_tokens=4096, messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Analyze the 3-year financial trends below. For each key area:\n"
                "1. Describe the trend (improving / declining / stable)\n"
                "2. Identify the likely drivers behind significant changes\n"
                "3. Highlight any red flags or notable strengths\n"
                "4. Provide an overall assessment of financial health trajectory\n\n"
                + prompt
            ),
        },
    ])


def analyze_stock_news_stream(symbol: str, company_name: str, sector: str, news_items: list):
    """
    Stream AI analysis of recent stock-specific news headlines.
    """
    if not news_items:
        return
    client = _get_client()
    from datetime import datetime

    lines = [
        f"Company: {company_name} ({symbol})",
        f"Sector: {sector}",
        "",
        "Recent News Headlines (newest first):",
    ]
    for item in news_items:
        title = item.get("title", "")
        publisher = item.get("publisher", "")
        ts = item.get("providerPublishTime", 0)
        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
        lines.append(f"  [{date_str}] {title}  ({publisher})")

    yield from _chat_stream(client, _effective_model(), max_tokens=2048, messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Based on the following recent news headlines for this stock:\n"
                "1. Summarize the key news themes and material events\n"
                "2. Assess the likely impact on the stock (positive / negative / neutral) and why\n"
                "3. Identify significant near-term risks or catalysts\n"
                "4. Give an overall news sentiment assessment\n\n"
                + "\n".join(lines)
            ),
        },
    ])


def analyze_industry_stream(
    sector: str,
    industry: str,
    company_name: str,
    news_items: list,
    peers: list | None = None,
):
    """
    Stream AI analysis of sector/industry news and competitive dynamics.

    peers: list of ticker symbols whose news was aggregated (for context).
    """
    if not news_items:
        return
    client = _get_client()
    from datetime import datetime

    peers_str = ", ".join(peers) if peers else "sector peers"
    lines = [
        f"Sector: {sector}",
        f"Industry: {industry}",
        f"Company of interest: {company_name}",
        f"News sourced from peers: {peers_str}",
        "",
        "Recent Peer/Industry News Headlines (newest first):",
    ]
    for item in news_items:
        title    = item.get("title", "")
        publisher= item.get("publisher", "")
        ts       = item.get("providerPublishTime", 0)
        tickers  = item.get("relatedTickers", [])
        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
        ticker_tag = f"[{', '.join(tickers[:4])}]" if tickers else ""
        lines.append(f"  [{date_str}] {ticker_tag} {title}  ({publisher})")

    yield from _chat_stream(client, _effective_model(), max_tokens=2048, messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "The following headlines were collected from major peers in the sector "
                f"({peers_str}). Based on this competitive intelligence:\n"
                "1. Identify the dominant industry themes and macro trends\n"
                "2. Assess competitive dynamics and any shifts in market structure\n"
                "3. Highlight major sector-wide opportunities and threats\n"
                "4. Evaluate the specific implications for the company mentioned above\n"
                "5. Provide an overall industry outlook (bullish / neutral / bearish)\n\n"
                + "\n".join(lines)
            ),
        },
    ])


_TA_SYSTEM = """You are a professional technical analyst specialising in price action and momentum.
Given technical indicator data, provide a clear, actionable trading idea.
Structure your response with these exact sections:
1. **Technical Summary** — overall trend (bullish / neutral / bearish) and key signals
2. **Trading Idea** — direction (long / short / wait) with indicator-based rationale
3. **Key Levels** — entry zone, price target(s), stop-loss
4. **Risk/Reward** — estimated ratio and timing horizon (swing: days–weeks, position: weeks–months)
5. **Key Risks** — what would invalidate this setup
End with a one-sentence verdict.
Note: educational purposes only, not investment advice."""


def analyze_technicals_stream(symbol: str, company_name: str, df, info: dict | None = None):
    """
    Stream an AI trading idea based on computed technical indicators.

    df must contain columns: Close, High, Low, Open, Volume,
    MA20, MA50, MA200, RSI, MACD, Signal, BB_upper, BB_lower, BB_mid
    """
    import pandas as pd

    client = _get_client()
    last  = df.iloc[-1]
    price = last["Close"]

    def _pct(n):
        if len(df) > n:
            return (price - df["Close"].iloc[-n - 1]) / df["Close"].iloc[-n - 1]
        return None

    vol_20avg = df["Volume"].rolling(20).mean().iloc[-1]
    vol_ratio = last["Volume"] / vol_20avg if vol_20avg and vol_20avg > 0 else None

    high_52 = df["High"].max()
    low_52  = df["Low"].min()
    pos_52  = (price - low_52) / (high_52 - low_52) if high_52 != low_52 else None

    rsi_val  = last["RSI"]
    macd_val = last["MACD"]
    sig_val  = last["Signal"]
    bb_upper = last["BB_upper"]
    bb_lower = last["BB_lower"]
    bb_mid   = last["BB_mid"]

    def _f(v, fmt=".2f"):
        return f"{v:{fmt}}" if pd.notna(v) else "N/A"

    def _above(cur, ref):
        return "above" if pd.notna(ref) and cur > ref else "below"

    bb_pos = (
        "near upper band" if pd.notna(bb_upper) and price >= 0.97 * bb_upper
        else "near lower band" if pd.notna(bb_lower) and price <= 1.03 * bb_lower
        else "mid-range"
    )
    rsi_label = (
        "Overbought" if pd.notna(rsi_val) and rsi_val > 70
        else "Oversold" if pd.notna(rsi_val) and rsi_val < 30
        else "Neutral"
    )
    macd_label = (
        "Bullish crossover" if pd.notna(macd_val) and pd.notna(sig_val) and macd_val > sig_val
        else "Bearish crossover"
    )

    perf_5d  = _pct(5)
    perf_20d = _pct(20)
    perf_60d = _pct(60)

    lines = [
        f"Symbol: {symbol}  ({company_name})",
        f"Sector: {info.get('sector', 'N/A')}" if info else "",
        f"Current Price: ${_f(price)}",
        "",
        "--- Price vs Moving Averages ---",
        f"MA20:  ${_f(last['MA20'])}  → {_above(price, last['MA20'])}",
        f"MA50:  ${_f(last['MA50'])}  → {_above(price, last['MA50'])}",
        f"MA200: ${_f(last['MA200'])} → {_above(price, last['MA200'])}",
        "",
        "--- Bollinger Bands (20, 2σ) ---",
        f"Upper: ${_f(bb_upper)}  Mid: ${_f(bb_mid)}  Lower: ${_f(bb_lower)}",
        f"Position: {bb_pos}",
        "",
        "--- Momentum ---",
        f"RSI(14): {_f(rsi_val, '.1f')}  ({rsi_label})",
        f"MACD: {_f(macd_val, '.4f')}  Signal: {_f(sig_val, '.4f')}  → {macd_label}",
        "",
        "--- Recent Performance ---",
        f"5-day:   {f'{perf_5d:+.1%}' if perf_5d is not None else 'N/A'}",
        f"20-day:  {f'{perf_20d:+.1%}' if perf_20d is not None else 'N/A'}",
        f"60-day:  {f'{perf_60d:+.1%}' if perf_60d is not None else 'N/A'}",
        f"52w range: ${_f(low_52)} – ${_f(high_52)}  "
        f"(currently at {f'{pos_52:.0%}' if pos_52 is not None else 'N/A'} of range)",
        "",
        "--- Volume ---",
        f"Latest vs 20-day avg: {f'{vol_ratio:.2f}x' if vol_ratio else 'N/A'}",
    ]

    yield from _chat_stream(client, _effective_model(), max_tokens=2048, messages=[
        {"role": "system", "content": _TA_SYSTEM},
        {
            "role": "user",
            "content": (
                "Generate a trading idea based on the following technical data:\n\n"
                + "\n".join(l for l in lines if l is not None)
            ),
        },
    ])


def compare_stocks_stream(infos: list[dict]):
    """
    Compare multiple stocks and recommend the best pick.
    Yields text chunks.
    """
    client = _get_client()

    blocks = []
    for info in infos:
        blocks.append(_format_metrics(info))

    combined = "\n\n" + ("=" * 60 + "\n").join(blocks)

    yield from _chat_stream(client, _effective_model(), max_tokens=4096, messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Compare these stocks side-by-side. "
                "Which offers the best risk/reward and why?\n\n"
                + combined
            ),
        },
    ])

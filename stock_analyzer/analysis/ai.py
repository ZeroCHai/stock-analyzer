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
    ARK_API_KEY, ARK_BASE_URL, MODEL,
    AI_PROVIDER, GCP_PROJECT, GCP_LOCATION,
    VOLC_AK, VOLC_SK, ARK_EP_MODEL,
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


def _get_client():
    """
    Return the appropriate AI client based on environment configuration.
    Automatically refreshes Vertex AI OAuth tokens before expiry.
    """
    global _client, _oauth_expires_at

    if AI_PROVIDER == "ark":
        if _client is None:
            if VOLC_AK and VOLC_SK:
                from volcenginesdkarkruntime import Ark
                _client = Ark(ak=VOLC_AK, sk=VOLC_SK)
            else:
                _client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
        return _client

    # Gemini — OAuth via Vertex AI
    if GCP_PROJECT:
        if time.time() >= _oauth_expires_at - 300:  # refresh 5 min before expiry
            _client, _oauth_expires_at = _make_vertex_client()
        return _client

    # Gemini — API key (default)
    if _client is None:
        _client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
    return _client


def _effective_model() -> str:
    """Return the model name appropriate for the active provider/auth mode."""
    if AI_PROVIDER == "ark":
        return ARK_EP_MODEL or MODEL
    if GCP_PROJECT:
        # Vertex AI OpenAI-compatible endpoint expects "google/<model-name>"
        return MODEL if MODEL.startswith("google/") else f"google/{MODEL}"
    return MODEL


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

    stream = client.chat.completions.create(
        model=_effective_model(),
        max_tokens=4096,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Please provide a comprehensive fundamental analysis "
                    "of the following stock:\n\n" + prompt
                ),
            },
        ],
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


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

    stream = client.chat.completions.create(
        model=_effective_model(),
        max_tokens=4096,
        stream=True,
        messages=[
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
        ],
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


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

    stream = client.chat.completions.create(
        model=_effective_model(),
        max_tokens=4096,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Compare these stocks side-by-side. "
                    "Which offers the best risk/reward and why?\n\n"
                    + combined
                ),
            },
        ],
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content

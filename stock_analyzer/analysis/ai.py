"""
AI-powered fundamental analysis using Seed2.0 via ByteDance Ark (OpenAI-compatible API).
"""

from __future__ import annotations
from openai import OpenAI
from stock_analyzer.config import ARK_API_KEY, ARK_BASE_URL, MODEL
from stock_analyzer.analysis.fundamental import extract_metrics, METRIC_LABELS

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
    return _client


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
        model=MODEL,
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
        model=MODEL,
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

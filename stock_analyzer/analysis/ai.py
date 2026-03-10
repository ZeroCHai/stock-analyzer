"""
AI-powered fundamental analysis using Claude (claude-opus-4-6).
Uses streaming + adaptive thinking for rich, reasoned reports.
"""

from __future__ import annotations
import anthropic
from stock_analyzer.config import ANTHROPIC_API_KEY, MODEL
from stock_analyzer.analysis.fundamental import extract_metrics, METRIC_LABELS

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
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
    Generator that yields text chunks from Claude's streaming response.
    Usage:
        for chunk in analyze_stock_stream(info):
            print(chunk, end="", flush=True)
    """
    client = _get_client()
    prompt = _format_metrics(info)

    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Please provide a comprehensive fundamental analysis "
                    "of the following stock:\n\n" + prompt
                ),
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            yield text


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

    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Compare these stocks side-by-side. "
                    "Which offers the best risk/reward and why?\n\n"
                    + combined
                ),
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            yield text

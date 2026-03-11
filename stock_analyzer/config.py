import os
from dotenv import load_dotenv

load_dotenv()


def _secret(key: str, default: str = "") -> str:
    """
    Read a config value with two-level fallback:
      1. Environment variable / .env file  (local dev)
      2. st.secrets                         (Streamlit Community Cloud)
    """
    val = os.getenv(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets.get(key, default))
    except Exception:
        return default


# ── Provider selection ────────────────────────────────────────────────────────
# "ark" (default) or "gemini"
AI_PROVIDER = _secret("AI_PROVIDER", "ark")

# ── ByteDance Ark / Seed2.0 ───────────────────────────────────────────────────
# Auth mode A — API key (simpler)
ARK_API_KEY  = _secret("ARK_API_KEY")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ARK_EP_MODEL = _secret("ARK_MODEL")          # endpoint ID, e.g. "ep-20250101-xxxxxx"

# Auth mode B — AK/SK (higher quota, needs volcenginesdkarkruntime)
VOLC_AK = _secret("VOLC_ACCESSKEY")
VOLC_SK = _secret("VOLC_SECRETKEY")

# ── Google Gemini ─────────────────────────────────────────────────────────────
# Auth mode A — API key
GEMINI_API_KEY  = _secret("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL    = _secret("GEMINI_MODEL", "gemini-2.0-flash")

# Auth mode B — Vertex AI OAuth (set GOOGLE_CLOUD_PROJECT to enable)
GCP_PROJECT  = _secret("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = _secret("GEMINI_LOCATION", "us-central1")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")

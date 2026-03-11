import os
from dotenv import load_dotenv

load_dotenv()

# ── Provider selection ────────────────────────────────────────────────────────
# "ark" (default) or "gemini"
AI_PROVIDER = os.getenv("AI_PROVIDER", "ark")

# ── ByteDance Ark / Seed2.0 ───────────────────────────────────────────────────
# Auth mode A — API key (simpler, set ARK_API_KEY in .env)
ARK_API_KEY  = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ARK_EP_MODEL = os.getenv("ARK_MODEL", "")          # endpoint ID, e.g. "ep-20250101-xxxxxx"

# Auth mode B — AK/SK (higher quota, needs volcenginesdkarkruntime)
VOLC_AK = os.getenv("VOLC_ACCESSKEY", "")
VOLC_SK = os.getenv("VOLC_SECRETKEY", "")

# ── Google Gemini ─────────────────────────────────────────────────────────────
# Auth mode A — API key
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Auth mode B — Vertex AI OAuth (set GOOGLE_CLOUD_PROJECT to enable)
GCP_PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION = os.getenv("GEMINI_LOCATION", "us-central1")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")

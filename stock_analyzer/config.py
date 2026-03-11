import os
from dotenv import load_dotenv

load_dotenv()

# ── Provider selection ────────────────────────────────────────────────────────
# AI_PROVIDER = "gemini" (default) or "ark" (ByteDance Volcano Engine)
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

# ── Gemini — API key mode (default) ──────────────────────────────────────────
ARK_API_KEY  = os.getenv("GEMINI_API_KEY", "")
ARK_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL        = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Gemini — Vertex AI OAuth mode ────────────────────────────────────────────
# Set GOOGLE_CLOUD_PROJECT to enable OAuth via Application Default Credentials.
# Run:  gcloud auth application-default login
# Or:   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION = os.getenv("GEMINI_LOCATION", "us-central1")

# ── ByteDance Ark / Seed2.0 — AK/SK mode ─────────────────────────────────────
# Set VOLC_ACCESSKEY + VOLC_SECRETKEY to use HMAC-signed requests (higher quota).
# ARK_MODEL must be set to a deployed endpoint ID (e.g. ep-20250101-xxxxxx).
VOLC_AK      = os.getenv("VOLC_ACCESSKEY", "")
VOLC_SK      = os.getenv("VOLC_SECRETKEY", "")
ARK_EP_MODEL = os.getenv("ARK_MODEL", "")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")

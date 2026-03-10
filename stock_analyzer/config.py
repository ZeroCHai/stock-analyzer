import os
from dotenv import load_dotenv

load_dotenv()

ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
# Model ID: find it in Ark console → Model Inference → My Endpoints
# e.g. "ep-20250311xxxxxx-xxxxx"  or the system model name "doubao-seed-2-0-250527"
MODEL = os.getenv("ARK_MODEL", "doubao-seed-2-0-250527")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")

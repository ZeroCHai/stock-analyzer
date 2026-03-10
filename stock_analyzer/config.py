import os
from dotenv import load_dotenv

load_dotenv()

ARK_API_KEY = os.getenv("GEMINI_API_KEY", "")
ARK_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")

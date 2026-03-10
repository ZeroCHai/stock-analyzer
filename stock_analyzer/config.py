import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stocks.db")
MODEL = "claude-opus-4-6"

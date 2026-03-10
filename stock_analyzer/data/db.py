"""SQLite persistence layer for cached stock data."""

import sqlite3
import json
from contextlib import contextmanager
from stock_analyzer.config import DB_PATH


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS stocks (
                symbol      TEXT PRIMARY KEY,
                name        TEXT,
                sector      TEXT,
                industry    TEXT,
                country     TEXT,
                fetched_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS financials (
                symbol      TEXT PRIMARY KEY,
                data        TEXT,   -- JSON blob from yfinance .info
                fetched_at  TEXT
            );
        """)


def upsert_stock(symbol: str, name: str, sector: str, industry: str, country: str):
    with _conn() as con:
        con.execute("""
            INSERT INTO stocks (symbol, name, sector, industry, country, fetched_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name, sector=excluded.sector,
                industry=excluded.industry, country=excluded.country,
                fetched_at=excluded.fetched_at
        """, (symbol, name, sector, industry, country))


def upsert_financials(symbol: str, data: dict):
    with _conn() as con:
        con.execute("""
            INSERT INTO financials (symbol, data, fetched_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(symbol) DO UPDATE SET
                data=excluded.data, fetched_at=excluded.fetched_at
        """, (symbol, json.dumps(data)))


def get_financials(symbol: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT data FROM financials WHERE symbol = ?", (symbol,)
        ).fetchone()
    return json.loads(row["data"]) if row else None


def list_cached_symbols() -> list[str]:
    with _conn() as con:
        rows = con.execute("SELECT symbol FROM stocks ORDER BY symbol").fetchall()
    return [r["symbol"] for r in rows]

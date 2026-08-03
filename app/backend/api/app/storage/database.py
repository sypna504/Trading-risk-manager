from __future__ import annotations

import sqlite3
from pathlib import Path

from ..config import settings


CREATE_DECISIONS_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    candles_count INTEGER NOT NULL,
    signal_detected INTEGER NOT NULL,
    active_strategies TEXT NOT NULL,
    selected_strategy TEXT,
    probability REAL,
    threshold REAL,
    risk_score REAL,
    risk_level TEXT,
    trade_allowed INTEGER NOT NULL,
    model_version TEXT,
    entry_price REAL,
    stop_loss_price REAL,
    take_profit_price REAL,
    position_size REAL,
    position_notional REAL,
    account_balance REAL,
    risk_per_trade_pct REAL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL
)
"""


def get_connection() -> sqlite3.Connection:
    path = Path(settings.DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with get_connection() as connection:
        connection.execute(CREATE_DECISIONS_SQL)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_created_at "
            "ON decisions(created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_symbol "
            "ON decisions(symbol)"
        )
        connection.commit()

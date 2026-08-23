from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

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
    reason TEXT NOT NULL,
    signal_timestamp TEXT,
    outcome_due_at TEXT,
    outcome_status TEXT NOT NULL DEFAULT 'pending',
    outcome_checked_at TEXT,
    realized_entry_price REAL,
    realized_exit_price REAL,
    realized_net_return REAL,
    realized_max_drawdown REAL,
    actual_target INTEGER,
    prediction_correct INTEGER,
    outcome_error TEXT,
    target_horizon_bars INTEGER NOT NULL DEFAULT 3,
    target_min_net_return REAL NOT NULL DEFAULT 0.002,
    target_max_drawdown REAL NOT NULL DEFAULT -0.015
)
"""

MIGRATION_COLUMNS = {
    "signal_timestamp": "TEXT",
    "outcome_due_at": "TEXT",
    "outcome_status": "TEXT NOT NULL DEFAULT 'pending'",
    "outcome_checked_at": "TEXT",
    "realized_entry_price": "REAL",
    "realized_exit_price": "REAL",
    "realized_net_return": "REAL",
    "realized_max_drawdown": "REAL",
    "actual_target": "INTEGER",
    "prediction_correct": "INTEGER",
    "outcome_error": "TEXT",
    "target_horizon_bars": "INTEGER NOT NULL DEFAULT 3",
    "target_min_net_return": "REAL NOT NULL DEFAULT 0.002",
    "target_max_drawdown": "REAL NOT NULL DEFAULT -0.015",
}


def get_connection() -> sqlite3.Connection:
    path = Path(settings.DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


def _migrate_decisions_table(connection: sqlite3.Connection) -> None:
    existing = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(decisions)").fetchall()
    }
    for column, sql_type in MIGRATION_COLUMNS.items():
        if column not in existing:
            connection.execute(
                f"ALTER TABLE decisions ADD COLUMN {column} {sql_type}"
            )


def init_database() -> None:
    with connection_scope() as connection:
        connection.execute(CREATE_DECISIONS_SQL)
        _migrate_decisions_table(connection)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_created_at "
            "ON decisions(created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_symbol "
            "ON decisions(symbol)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_outcome_due "
            "ON decisions(outcome_status, outcome_due_at)"
        )
        connection.commit()

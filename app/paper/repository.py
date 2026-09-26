from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import PaperPortfolio, VirtualPosition


class PaperRepository:
    def __init__(self, database_path: str | Path, *, starting_balance: float = 10_000.0) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.starting_balance = starting_balance
        self._init_schema()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self):
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS paper_portfolios(
                    portfolio_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL, updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS paper_positions(
                    id TEXT PRIMARY KEY, decision_id INTEGER UNIQUE NOT NULL, symbol TEXT NOT NULL,
                    status TEXT NOT NULL, payload_json TEXT NOT NULL, opened_at TEXT, exit_at TEXT
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS paper_equity(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL, equity REAL NOT NULL
                )"""
            )
            connection.commit()
        if self.get_portfolio() is None:
            self.save_portfolio(PaperPortfolio(starting_balance=self.starting_balance, current_equity=self.starting_balance, cash=self.starting_balance, peak_equity=self.starting_balance))

    def save_portfolio(self, portfolio: PaperPortfolio) -> PaperPortfolio:
        payload = portfolio.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO paper_portfolios(portfolio_id,payload_json,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(portfolio_id) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at",
                (portfolio.portfolio_id, json.dumps(payload), portfolio.updated_at.isoformat()),
            )
            connection.execute(
                "INSERT INTO paper_equity(portfolio_id,timestamp,equity) VALUES(?,?,?)",
                (portfolio.portfolio_id, portfolio.updated_at.isoformat(), portfolio.current_equity),
            )
            connection.commit()
        return portfolio

    def get_portfolio(self) -> PaperPortfolio | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM paper_portfolios WHERE portfolio_id='default'").fetchone()
        return PaperPortfolio.model_validate(json.loads(row["payload_json"])) if row else None

    def save_position(self, position: VirtualPosition) -> VirtualPosition:
        payload = position.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO paper_positions(id,decision_id,symbol,status,payload_json,opened_at,exit_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status,payload_json=excluded.payload_json,
                    opened_at=excluded.opened_at,exit_at=excluded.exit_at""",
                (position.id, position.decision_id, position.symbol, position.status.value,
                 json.dumps(payload), position.opened_at.isoformat() if position.opened_at else None,
                 position.exit_at.isoformat() if position.exit_at else None),
            )
            connection.commit()
        return position

    def get_position(self, position_id: str) -> VirtualPosition | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM paper_positions WHERE id=?", (position_id,)).fetchone()
        return VirtualPosition.model_validate(json.loads(row["payload_json"])) if row else None

    def get_by_decision(self, decision_id: int) -> VirtualPosition | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM paper_positions WHERE decision_id=?", (decision_id,)).fetchone()
        return VirtualPosition.model_validate(json.loads(row["payload_json"])) if row else None

    def list_positions(self, *, open_only: bool = False, limit: int = 500) -> list[VirtualPosition]:
        sql = "SELECT payload_json FROM paper_positions"
        values: list = []
        if open_only:
            sql += " WHERE status IN ('pending_entry','open')"
        sql += " ORDER BY COALESCE(opened_at, '') DESC LIMIT ?"
        values.append(max(1, min(limit, 1000)))
        with self._connect() as connection:
            rows = connection.execute(sql, values).fetchall()
        return [VirtualPosition.model_validate(json.loads(row["payload_json"])) for row in rows]

    def equity_curve(self, limit: int = 5000) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT timestamp,equity FROM paper_equity WHERE portfolio_id='default' ORDER BY id DESC LIMIT ?",
                (max(1,min(limit,5000)),),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

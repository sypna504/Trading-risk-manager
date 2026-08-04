from __future__ import annotations

import json
from typing import Any

from .database import connection_scope


class DecisionRepository:
    INSERT_COLUMNS = [
        "created_at",
        "exchange",
        "symbol",
        "interval",
        "candles_count",
        "signal_detected",
        "active_strategies",
        "selected_strategy",
        "probability",
        "threshold",
        "risk_score",
        "risk_level",
        "trade_allowed",
        "model_version",
        "entry_price",
        "stop_loss_price",
        "take_profit_price",
        "position_size",
        "position_notional",
        "account_balance",
        "risk_per_trade_pct",
        "status",
        "reason",
    ]

    @staticmethod
    def _serialize(decision: dict[str, Any]) -> dict[str, Any]:
        result = dict(decision)
        result["signal_detected"] = int(bool(result["signal_detected"]))
        result["trade_allowed"] = int(bool(result["trade_allowed"]))
        result["active_strategies"] = json.dumps(
            result.get("active_strategies", []),
            ensure_ascii=False,
        )
        return result

    @staticmethod
    def _deserialize(row) -> dict[str, Any] | None:
        if row is None:
            return None

        result = dict(row)
        result["signal_detected"] = bool(result["signal_detected"])
        result["trade_allowed"] = bool(result["trade_allowed"])
        result["active_strategies"] = json.loads(
            result["active_strategies"] or "[]"
        )
        return result

    def save(self, decision: dict[str, Any]) -> int:
        payload = self._serialize(decision)
        placeholders = ", ".join("?" for _ in self.INSERT_COLUMNS)
        columns = ", ".join(self.INSERT_COLUMNS)
        values = [payload.get(column) for column in self.INSERT_COLUMNS]

        with connection_scope() as connection:
            cursor = connection.execute(
                f"INSERT INTO decisions ({columns}) VALUES ({placeholders})",
                values,
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get(self, decision_id: int) -> dict[str, Any] | None:
        with connection_scope() as connection:
            row = connection.execute(
                "SELECT * FROM decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()
        return self._deserialize(row)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        symbol: str | None = None,
        strategy: str | None = None,
        trade_allowed: bool | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        values: list[Any] = []

        if symbol:
            where.append("symbol = ?")
            values.append(symbol.upper())
        if strategy:
            where.append("selected_strategy = ?")
            values.append(strategy)
        if trade_allowed is not None:
            where.append("trade_allowed = ?")
            values.append(int(trade_allowed))

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        values.extend([limit, offset])

        with connection_scope() as connection:
            rows = connection.execute(
                "SELECT * FROM decisions"
                + where_sql
                + " ORDER BY id DESC LIMIT ? OFFSET ?",
                values,
            ).fetchall()

        return [self._deserialize(row) for row in rows]

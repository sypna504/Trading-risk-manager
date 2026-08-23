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
        "signal_timestamp",
        "outcome_due_at",
        "outcome_status",
        "target_horizon_bars",
        "target_min_net_return",
        "target_max_drawdown",
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
        if result.get("actual_target") is not None:
            result["actual_target"] = bool(result["actual_target"])
        if result.get("prediction_correct") is not None:
            result["prediction_correct"] = bool(result["prediction_correct"])
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
        outcome_status: str | None = None,
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
        if outcome_status:
            where.append("outcome_status = ?")
            values.append(outcome_status)

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

    def list_due_outcomes(
        self,
        *,
        now_iso: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with connection_scope() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM decisions
                WHERE outcome_status IN ('pending', 'retry')
                  AND signal_detected = 1
                  AND outcome_due_at IS NOT NULL
                  AND outcome_due_at <= ?
                ORDER BY outcome_due_at ASC, id ASC
                LIMIT ?
                """,
                (now_iso, limit),
            ).fetchall()
        return [self._deserialize(row) for row in rows]

    def mark_outcome_completed(
        self,
        decision_id: int,
        outcome: dict[str, Any],
    ) -> None:
        with connection_scope() as connection:
            connection.execute(
                """
                UPDATE decisions
                SET outcome_status = 'completed',
                    outcome_checked_at = ?,
                    realized_entry_price = ?,
                    realized_exit_price = ?,
                    realized_net_return = ?,
                    realized_max_drawdown = ?,
                    actual_target = ?,
                    prediction_correct = ?,
                    outcome_error = NULL
                WHERE id = ?
                """,
                (
                    outcome["outcome_checked_at"],
                    outcome["realized_entry_price"],
                    outcome["realized_exit_price"],
                    outcome["realized_net_return"],
                    outcome["realized_max_drawdown"],
                    int(outcome["actual_target"]),
                    int(outcome["prediction_correct"]),
                    decision_id,
                ),
            )
            connection.commit()

    def mark_outcome_retry(
        self,
        decision_id: int,
        *,
        checked_at: str,
        error: str,
    ) -> None:
        with connection_scope() as connection:
            connection.execute(
                """
                UPDATE decisions
                SET outcome_status = 'retry',
                    outcome_checked_at = ?,
                    outcome_error = ?
                WHERE id = ?
                """,
                (checked_at, error[:1000], decision_id),
            )
            connection.commit()

    def outcome_summary(self) -> dict[str, Any]:
        with connection_scope() as connection:
            totals = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN outcome_status = 'completed' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN outcome_status IN ('pending', 'retry') THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN prediction_correct = 1 THEN 1 ELSE 0 END) AS correct,
                    SUM(CASE WHEN prediction_correct = 0 THEN 1 ELSE 0 END) AS incorrect,
                    SUM(CASE WHEN trade_allowed = 1 AND actual_target = 1 THEN 1 ELSE 0 END) AS true_positive,
                    SUM(CASE WHEN trade_allowed = 1 AND actual_target = 0 THEN 1 ELSE 0 END) AS false_positive,
                    SUM(CASE WHEN trade_allowed = 0 AND actual_target = 1 THEN 1 ELSE 0 END) AS false_negative,
                    SUM(CASE WHEN trade_allowed = 0 AND actual_target = 0 THEN 1 ELSE 0 END) AS true_negative
                FROM decisions
                WHERE signal_detected = 1
                """
            ).fetchone()

            by_strategy = connection.execute(
                """
                SELECT
                    selected_strategy,
                    COUNT(*) AS completed,
                    AVG(CASE WHEN prediction_correct = 1 THEN 1.0 ELSE 0.0 END) AS accuracy,
                    AVG(realized_net_return) AS mean_net_return
                FROM decisions
                WHERE outcome_status = 'completed'
                GROUP BY selected_strategy
                ORDER BY selected_strategy
                """
            ).fetchall()

        result = dict(totals)
        completed = int(result.get("completed") or 0)
        correct = int(result.get("correct") or 0)
        result["accuracy"] = correct / completed if completed else None
        result["by_strategy"] = {
            str(row["selected_strategy"]): {
                "completed": int(row["completed"]),
                "accuracy": float(row["accuracy"]),
                "mean_net_return": float(row["mean_net_return"]),
            }
            for row in by_strategy
        }
        return result

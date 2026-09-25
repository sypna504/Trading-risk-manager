from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import settings
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
        "raw_probability",
        "threshold",
        "risk_score",
        "risk_level",
        "trade_allowed",
        "model_version",
        "feature_schema_version",
        "model_status",
        "calibration_method",
        "market_regime",
        "entry_price",
        "signal_close_price",
        "planned_entry_price",
        "entry_convention",
        "exit_convention",
        "stop_loss_price",
        "take_profit_price",
        "position_size",
        "position_notional",
        "account_balance",
        "risk_per_trade_pct",
        "status",
        "reason",
        "news_context_available",
        "news_risk_level",
        "news_count",
        "high_impact_news_count",
        "signal_timestamp",
        "outcome_due_at",
        "outcome_status",
        "target_definition",
        "target_horizon_minutes",
        "target_horizon_bars",
        "target_min_net_return",
        "target_max_drawdown",
        "target_fee",
        "target_slippage",
        "target_stop_loss_fraction",
        "target_risk_reward_ratio",
        "target_intrabar_priority",
    ]

    @staticmethod
    def _serialize(decision: dict[str, Any]) -> dict[str, Any]:
        result = dict(decision)
        signal_detected = bool(result.get("signal_detected", False))
        result["signal_detected"] = int(signal_detected)
        result["trade_allowed"] = int(bool(result.get("trade_allowed", False)))
        result["news_context_available"] = int(
            bool(result.get("news_context_available", False))
        )
        result["news_count"] = int(result.get("news_count") or 0)
        result["high_impact_news_count"] = int(
            result.get("high_impact_news_count") or 0
        )
        result["active_strategies"] = json.dumps(
            result.get("active_strategies", []),
            ensure_ascii=False,
        )
        # Keep direct/legacy repository callers compatible with the expanded
        # outcome schema. Current API paths still pass an immutable model-target
        # snapshot explicitly, so these defaults are only a safe fallback.
        if not result.get("outcome_status"):
            result["outcome_status"] = (
                "pending" if signal_detected else "not_applicable"
            )
        defaults = {
            "target_definition": "horizon_return_drawdown",
            "target_horizon_minutes": settings.OUTCOME_TARGET_HORIZON_MINUTES,
            "target_horizon_bars": settings.OUTCOME_TARGET_HORIZON_BARS,
            "target_min_net_return": settings.OUTCOME_MIN_NET_RETURN,
            "target_max_drawdown": settings.OUTCOME_MAX_DRAWDOWN,
            "target_fee": settings.OUTCOME_FEE,
            "target_slippage": settings.OUTCOME_SLIPPAGE,
        }
        for field, fallback in defaults.items():
            if result.get(field) is None:
                result[field] = fallback
        if result.get("raw_probability") is None and result.get("probability") is not None:
            result["raw_probability"] = result["probability"]
        return result

    @staticmethod
    def _deserialize(row) -> dict[str, Any] | None:
        if row is None:
            return None
        result = dict(row)
        result["signal_detected"] = bool(result["signal_detected"])
        result["trade_allowed"] = bool(result["trade_allowed"])
        result["news_context_available"] = bool(
            result.get("news_context_available", 0)
        )
        result["active_strategies"] = json.loads(result["active_strategies"] or "[]")
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
                "SELECT * FROM decisions WHERE id = ?", (decision_id,)
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
                    realized_exit_reason = ?,
                    realized_holding_bars = ?,
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
                    outcome.get("realized_exit_reason"),
                    outcome.get("realized_holding_bars"),
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
                    outcome_attempts = outcome_attempts + 1,
                    outcome_checked_at = ?,
                    outcome_error = ?
                WHERE id = ?
                """,
                (checked_at, error[:1000], decision_id),
            )
            connection.commit()

    def mark_outcome_invalid(
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
                SET outcome_status = 'invalid_data',
                    outcome_attempts = outcome_attempts + 1,
                    outcome_checked_at = ?,
                    outcome_error = ?
                WHERE id = ?
                """,
                (checked_at, error[:1000], decision_id),
            )
            connection.commit()

    @staticmethod
    def _safe_ratio(numerator: int | float, denominator: int | float) -> float | None:
        return float(numerator / denominator) if denominator else None

    @staticmethod
    def _group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row.get(key) or "unknown")].append(row)
        result: dict[str, dict[str, Any]] = {}
        for name, part in groups.items():
            returns = [
                float(row["realized_net_return"])
                for row in part
                if row.get("realized_net_return") is not None
            ]
            correct = sum(bool(row.get("prediction_correct")) for row in part)
            result[name] = {
                "completed": len(part),
                "accuracy": correct / len(part) if part else None,
                "mean_net_return": sum(returns) / len(returns) if returns else None,
                "total_net_return": sum(returns) if returns else 0.0,
            }
        return result

    @staticmethod
    def _calibration_bins(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bins: list[dict[str, Any]] = []
        for index in range(10):
            left = index / 10
            right = (index + 1) / 10
            part = [
                row
                for row in rows
                if row.get("probability") is not None
                and (
                    left <= float(row["probability"]) <= right
                    if index == 9
                    else left <= float(row["probability"]) < right
                )
            ]
            if not part:
                continue
            probabilities = [float(row["probability"]) for row in part]
            observed = [int(bool(row["actual_target"])) for row in part]
            returns = [
                float(row["realized_net_return"])
                for row in part
                if row.get("realized_net_return") is not None
            ]
            bins.append(
                {
                    "bin": f"{left:.1f}-{right:.1f}",
                    "count": len(part),
                    "mean_predicted_probability": sum(probabilities) / len(probabilities),
                    "observed_positive_rate": sum(observed) / len(observed),
                    "mean_realized_net_return": (
                        sum(returns) / len(returns) if returns else None
                    ),
                }
            )
        return bins

    def outcome_summary(self) -> dict[str, Any]:
        with connection_scope() as connection:
            all_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM decisions WHERE signal_detected = 1"
                ).fetchall()
            ]
        completed_rows = [
            row for row in all_rows if row.get("outcome_status") == "completed"
        ]
        pending = sum(
            row.get("outcome_status") in {"pending", "retry"}
            for row in all_rows
        )
        invalid_data = sum(
            row.get("outcome_status") == "invalid_data" for row in all_rows
        )
        tp = sum(bool(row.get("trade_allowed")) and bool(row.get("actual_target")) for row in completed_rows)
        fp = sum(bool(row.get("trade_allowed")) and not bool(row.get("actual_target")) for row in completed_rows)
        fn = sum(not bool(row.get("trade_allowed")) and bool(row.get("actual_target")) for row in completed_rows)
        tn = sum(not bool(row.get("trade_allowed")) and not bool(row.get("actual_target")) for row in completed_rows)
        correct = tp + tn
        incorrect = fp + fn

        probabilities = [
            float(row["probability"])
            for row in completed_rows
            if row.get("probability") is not None
        ]
        targets = [
            float(bool(row["actual_target"]))
            for row in completed_rows
            if row.get("probability") is not None
        ]
        brier = (
            sum((p - y) ** 2 for p, y in zip(probabilities, targets)) / len(probabilities)
            if probabilities
            else None
        )
        returns = [
            float(row["realized_net_return"])
            for row in completed_rows
            if row.get("realized_net_return") is not None
        ]

        now = datetime.now(timezone.utc)

        def window(days: int) -> dict[str, Any]:
            cutoff = now - timedelta(days=days)
            part = []
            for row in completed_rows:
                raw = row.get("outcome_checked_at") or row.get("created_at")
                if not raw:
                    continue
                parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed.astimezone(timezone.utc) >= cutoff:
                    part.append(row)
            part_returns = [
                float(row["realized_net_return"])
                for row in part
                if row.get("realized_net_return") is not None
            ]
            return {
                "completed": len(part),
                "mean_net_return": (
                    sum(part_returns) / len(part_returns) if part_returns else None
                ),
                "total_net_return": sum(part_returns) if part_returns else 0.0,
                "mean_probability": (
                    sum(float(row["probability"]) for row in part if row.get("probability") is not None)
                    / max(sum(row.get("probability") is not None for row in part), 1)
                    if any(row.get("probability") is not None for row in part)
                    else None
                ),
            }

        return {
            "total": len(all_rows),
            "completed": len(completed_rows),
            "pending": int(pending),
            "invalid_data": int(invalid_data),
            "correct": correct,
            "incorrect": incorrect,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
            "precision": self._safe_ratio(tp, tp + fp),
            "recall": self._safe_ratio(tp, tp + fn),
            "specificity": self._safe_ratio(tn, tn + fp),
            "false_positive_rate": self._safe_ratio(fp, fp + tn),
            "false_negative_rate": self._safe_ratio(fn, fn + tp),
            "accuracy": self._safe_ratio(correct, len(completed_rows)),
            "brier_score": brier,
            "mean_realized_net_return": (
                sum(returns) / len(returns) if returns else None
            ),
            "total_realized_net_return": sum(returns) if returns else 0.0,
            "missed_good_trades": fn,
            "bad_allowed_trades": fp,
            "calibration_bins": self._calibration_bins(completed_rows),
            "by_symbol": self._group_rows(completed_rows, "symbol"),
            "by_strategy": self._group_rows(completed_rows, "selected_strategy"),
            "by_interval": self._group_rows(completed_rows, "interval"),
            "by_model_version": self._group_rows(completed_rows, "model_version"),
            "by_market_regime": self._group_rows(completed_rows, "market_regime"),
            "rolling_7d": window(7),
            "rolling_30d": window(30),
        }

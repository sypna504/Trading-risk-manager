from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import settings
from ..storage.decision_repository import DecisionRepository
from .market_services import Candle, GetCandles


logger = logging.getLogger(__name__)


def interval_to_timedelta(interval: str) -> timedelta:
    value = interval.strip().lower()
    if len(value) < 2:
        raise ValueError(f"invalid interval: {interval}")
    amount = int(value[:-1])
    units = {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
    }
    try:
        return units[value[-1]]
    except KeyError as error:
        raise ValueError(f"unsupported interval: {interval}") from error


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def outcome_due_at(
    signal_timestamp: str,
    interval: str,
    horizon_bars: int,
) -> str:
    if horizon_bars < 1:
        raise ValueError("horizon_bars must be positive")
    signal_time = parse_utc(signal_timestamp)
    due = signal_time + interval_to_timedelta(interval) * (horizon_bars + 1)
    return due.isoformat()


@dataclass(frozen=True)
class OutcomeResult:
    realized_entry_price: float
    realized_exit_price: float
    realized_net_return: float
    realized_max_drawdown: float
    actual_target: bool
    prediction_correct: bool

    def as_dict(self, checked_at: str) -> dict[str, Any]:
        return {
            "outcome_checked_at": checked_at,
            "realized_entry_price": self.realized_entry_price,
            "realized_exit_price": self.realized_exit_price,
            "realized_net_return": self.realized_net_return,
            "realized_max_drawdown": self.realized_max_drawdown,
            "actual_target": self.actual_target,
            "prediction_correct": self.prediction_correct,
        }


def calculate_outcome(
    *,
    decision: dict[str, Any],
    candles: list[Candle],
) -> OutcomeResult:
    signal_timestamp = parse_utc(str(decision["signal_timestamp"]))
    horizon = int(decision["target_horizon_bars"])
    future = sorted(
        (
            candle
            for candle in candles
            if candle.timestamp.astimezone(timezone.utc) > signal_timestamp
        ),
        key=lambda candle: candle.timestamp,
    )

    if len(future) < horizon:
        raise ValueError(
            f"not enough closed candles for outcome: {len(future)} < {horizon}"
        )

    selected = future[:horizon]
    entry_price = float(selected[0].open)
    exit_price = float(selected[-1].close)
    future_min_low = min(float(candle.low) for candle in selected)

    round_trip_cost = 2 * (settings.OUTCOME_FEE + settings.OUTCOME_SLIPPAGE)
    net_return = exit_price / entry_price - 1 - round_trip_cost
    max_drawdown = future_min_low / entry_price - 1

    min_return = float(decision["target_min_net_return"])
    max_allowed_drawdown = float(decision["target_max_drawdown"])
    actual_target = (
        net_return > min_return
        and max_drawdown > max_allowed_drawdown
    )
    predicted_target = bool(decision["trade_allowed"])

    return OutcomeResult(
        realized_entry_price=entry_price,
        realized_exit_price=exit_price,
        realized_net_return=net_return,
        realized_max_drawdown=max_drawdown,
        actual_target=actual_target,
        prediction_correct=predicted_target == actual_target,
    )


class OutcomeEvaluator:
    def __init__(
        self,
        repository: DecisionRepository | None = None,
    ) -> None:
        self.repository = repository or DecisionRepository()

    @staticmethod
    def _download(decision: dict[str, Any]) -> list[Candle]:
        horizon = int(decision["target_horizon_bars"])
        downloader = GetCandles(
            symbol=str(decision["symbol"]),
            interval=str(decision["interval"]),
            limit=max(60, horizon + 10),
        )
        if decision["exchange"] == "bybit":
            return downloader.get_bybit_candles_dc().items
        return downloader.get_binance_candles().items

    def evaluate_decision(
        self,
        decision: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        checked_at = (now or datetime.now(timezone.utc)).isoformat()
        candles = self._download(decision)
        result = calculate_outcome(decision=decision, candles=candles)
        payload = result.as_dict(checked_at)
        self.repository.mark_outcome_completed(int(decision["id"]), payload)
        return payload

    def run_once(
        self,
        *,
        now: datetime | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        current = now or datetime.now(timezone.utc)
        decisions = self.repository.list_due_outcomes(
            now_iso=current.isoformat(),
            limit=limit or settings.OUTCOME_BATCH_SIZE,
        )
        completed = 0
        retries = 0
        errors: dict[int, str] = {}

        for decision in decisions:
            try:
                self.evaluate_decision(decision, now=current)
                completed += 1
            except Exception as error:
                retries += 1
                errors[int(decision["id"])] = str(error)
                self.repository.mark_outcome_retry(
                    int(decision["id"]),
                    checked_at=current.isoformat(),
                    error=str(error),
                )
                logger.warning(
                    "outcome evaluation failed decision_id=%s error=%s",
                    decision["id"],
                    error,
                )

        return {
            "checked": len(decisions),
            "completed": completed,
            "retries": retries,
            "errors": errors,
        }


class OutcomeWorker:
    def __init__(self, evaluator: OutcomeEvaluator | None = None) -> None:
        self.evaluator = evaluator or OutcomeEvaluator()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not settings.OUTCOME_AUTO_EVALUATION:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="decision-outcome-worker",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.evaluator.run_once()
            except Exception:
                logger.exception("outcome worker iteration failed")
            self._stop.wait(settings.OUTCOME_CHECK_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

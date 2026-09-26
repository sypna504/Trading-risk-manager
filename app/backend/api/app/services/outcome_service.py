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


class OutcomeDataError(ValueError):
    pass


class OutcomeNotReadyError(OutcomeDataError):
    pass


class OutcomeDataGapError(OutcomeDataError):
    pass


def interval_to_timedelta(interval: str) -> timedelta:
    value = interval.strip().lower()
    if len(value) < 2:
        raise ValueError(f"invalid interval: {interval}")
    amount = int(value[:-1])
    if amount <= 0:
        raise ValueError(f"invalid interval: {interval}")
    units = {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
    }
    try:
        return units[value[-1]]
    except KeyError as error:
        raise ValueError(f"unsupported interval: {interval}") from error


def parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def outcome_due_at(signal_timestamp: str, interval: str, horizon_bars: int) -> str:
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
    realized_exit_reason: str
    realized_holding_bars: int
    actual_target: bool
    prediction_correct: bool

    def as_dict(self, checked_at: str) -> dict[str, Any]:
        return {
            "outcome_checked_at": checked_at,
            "realized_entry_price": self.realized_entry_price,
            "realized_exit_price": self.realized_exit_price,
            "realized_net_return": self.realized_net_return,
            "realized_max_drawdown": self.realized_max_drawdown,
            "realized_exit_reason": self.realized_exit_reason,
            "realized_holding_bars": self.realized_holding_bars,
            "actual_target": self.actual_target,
            "prediction_correct": self.prediction_correct,
        }


def expected_outcome_timestamps(decision: dict[str, Any]) -> list[datetime]:
    signal_timestamp = parse_utc(str(decision["signal_timestamp"]))
    horizon = int(decision["target_horizon_bars"])
    if horizon < 1:
        raise ValueError("target_horizon_bars must be positive")
    delta = interval_to_timedelta(str(decision.get("interval") or "1h"))
    return [signal_timestamp + delta * step for step in range(1, horizon + 1)]


def _anchored_closed_candles(
    decision: dict[str, Any],
    candles: list[Candle],
    *,
    now: datetime,
) -> list[Candle]:
    expected = expected_outcome_timestamps(decision)
    delta = interval_to_timedelta(str(decision.get("interval") or "1h"))
    current = parse_utc(now)
    by_timestamp = {parse_utc(candle.timestamp): candle for candle in candles}
    missing = [timestamp for timestamp in expected if timestamp not in by_timestamp]
    if missing:
        raise OutcomeDataGapError(
            "not enough closed candles for the anchored outcome horizon; missing="
            + str([timestamp.isoformat() for timestamp in missing])
        )
    not_closed = [timestamp for timestamp in expected if timestamp + delta > current]
    if not_closed:
        raise OutcomeNotReadyError(
            "outcome window is not fully closed yet; first_open_bar="
            + not_closed[0].isoformat()
        )
    return [by_timestamp[timestamp] for timestamp in expected]


def _legacy_horizon_outcome(
    decision: dict[str, Any],
    selected: list[Candle],
) -> tuple[float, float, str, int, bool]:
    entry = float(selected[0].open)
    exit_price = float(selected[-1].close)
    low = min(float(candle.low) for candle in selected)
    fee = float(decision.get("target_fee", settings.OUTCOME_FEE))
    slippage = float(decision.get("target_slippage", settings.OUTCOME_SLIPPAGE))
    net_return = exit_price / entry - 1 - 2 * (fee + slippage)
    max_drawdown = low / entry - 1
    actual_target = (
        net_return > float(decision.get("target_min_net_return", settings.OUTCOME_MIN_NET_RETURN))
        and max_drawdown > float(decision.get("target_max_drawdown", settings.OUTCOME_MAX_DRAWDOWN))
    )
    return exit_price, max_drawdown, "horizon_close", len(selected), actual_target


def _first_touch_outcome(
    decision: dict[str, Any],
    selected: list[Candle],
) -> tuple[float, float, str, int, bool]:
    entry = float(selected[0].open)
    stop_fraction = decision.get("target_stop_loss_fraction")
    if stop_fraction is None:
        raise OutcomeDataError("first-touch outcome is missing target_stop_loss_fraction snapshot")
    stop_fraction = float(stop_fraction)
    if not 0 < stop_fraction < 1:
        raise OutcomeDataError("target_stop_loss_fraction must be between 0 and 1")
    rr = float(decision.get("target_risk_reward_ratio") or 2.0)
    if rr < 1:
        raise OutcomeDataError("target_risk_reward_ratio must be at least 1")
    intrabar = str(decision.get("target_intrabar_priority") or "stop_loss")
    if intrabar != "stop_loss":
        raise OutcomeDataError("only conservative stop_loss intrabar priority is supported")

    stop = entry * (1.0 - stop_fraction)
    take_profit = entry * (1.0 + stop_fraction * rr)
    running_low = entry
    exit_price = float(selected[-1].close)
    exit_reason = "timeout"
    holding_bars = len(selected)
    for index, candle in enumerate(selected, start=1):
        candle_open = float(candle.open)
        candle_low = float(candle.low)
        candle_high = float(candle.high)
        running_low = min(running_low, candle_low)
        # Same-bar ambiguity is resolved conservatively in favour of SL.
        if candle_low <= stop:
            exit_price = min(candle_open, stop)
            exit_reason = "stop_loss"
            holding_bars = index
            break
        if candle_high >= take_profit:
            exit_price = take_profit
            exit_reason = "take_profit"
            holding_bars = index
            break
    max_drawdown = running_low / entry - 1.0
    return exit_price, max_drawdown, exit_reason, holding_bars, exit_reason == "take_profit"


def calculate_outcome(
    *,
    decision: dict[str, Any],
    candles: list[Candle],
    now: datetime | None = None,
) -> OutcomeResult:
    current = parse_utc(now or datetime.now(timezone.utc))
    selected = _anchored_closed_candles(decision, candles, now=current)
    entry_price = float(selected[0].open)
    target_definition = str(
        decision.get("target_definition") or "horizon_return_drawdown"
    )
    if target_definition == "first_touch_atr_rr":
        exit_price, max_drawdown, exit_reason, holding_bars, actual_target = (
            _first_touch_outcome(decision, selected)
        )
    elif target_definition == "horizon_return_drawdown":
        exit_price, max_drawdown, exit_reason, holding_bars, actual_target = (
            _legacy_horizon_outcome(decision, selected)
        )
    else:
        raise OutcomeDataError(f"unsupported target_definition snapshot: {target_definition}")

    fee = float(decision.get("target_fee", settings.OUTCOME_FEE))
    slippage = float(decision.get("target_slippage", settings.OUTCOME_SLIPPAGE))
    net_return = exit_price / entry_price - 1.0 - 2 * (fee + slippage)
    predicted_target = bool(decision["trade_allowed"])
    return OutcomeResult(
        realized_entry_price=entry_price,
        realized_exit_price=exit_price,
        realized_net_return=net_return,
        realized_max_drawdown=max_drawdown,
        realized_exit_reason=exit_reason,
        realized_holding_bars=holding_bars,
        actual_target=actual_target,
        prediction_correct=predicted_target == actual_target,
    )


class OutcomeEvaluator:
    def __init__(self, repository: DecisionRepository | None = None) -> None:
        self.repository = repository or DecisionRepository()

    @staticmethod
    def _download(decision: dict[str, Any]) -> list[Candle]:
        expected = expected_outcome_timestamps(decision)
        delta = interval_to_timedelta(str(decision["interval"]))
        since = expected[0]
        until = expected[-1] + delta
        downloader = GetCandles(
            symbol=str(decision["symbol"]),
            interval=str(decision["interval"]),
            limit=max(60, len(expected) + 10),
        )
        if str(decision["exchange"]).lower() == "bybit":
            return downloader.get_bybit_candles_range(since=since, until=until).items
        return downloader.get_binance_candles_range(since=since, until=until).items

    def evaluate_decision(
        self,
        decision: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = now or datetime.now(timezone.utc)
        checked_at = current.astimezone(timezone.utc).isoformat()
        result = calculate_outcome(
            decision=decision,
            candles=self._download(decision),
            now=current,
        )
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
        completed = retries = invalid_data = 0
        errors: dict[int, str] = {}
        for decision in decisions:
            decision_id = int(decision["id"])
            try:
                self.evaluate_decision(decision, now=current)
                completed += 1
            except OutcomeDataGapError as error:
                attempts = int(decision.get("outcome_attempts") or 0) + 1
                errors[decision_id] = str(error)
                if attempts >= settings.OUTCOME_MAX_RETRIES:
                    invalid_data += 1
                    self.repository.mark_outcome_invalid(
                        decision_id, checked_at=current.isoformat(), error=str(error)
                    )
                else:
                    retries += 1
                    self.repository.mark_outcome_retry(
                        decision_id, checked_at=current.isoformat(), error=str(error)
                    )
            except (OutcomeNotReadyError, ConnectionError) as error:
                retries += 1
                errors[decision_id] = str(error)
                self.repository.mark_outcome_retry(
                    decision_id, checked_at=current.isoformat(), error=str(error)
                )
            except Exception as error:
                retries += 1
                errors[decision_id] = str(error)
                self.repository.mark_outcome_retry(
                    decision_id, checked_at=current.isoformat(), error=str(error)
                )
                logger.exception(
                    "unexpected outcome evaluation error decision_id=%s", decision_id
                )
        return {
            "checked": len(decisions),
            "completed": completed,
            "retries": retries,
            "invalid_data": invalid_data,
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

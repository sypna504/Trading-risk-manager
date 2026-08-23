from datetime import datetime, timezone

import pytest

from app.backend.api.app.config import settings
from app.backend.api.app.services.market_services import Candle
from app.backend.api.app.services.outcome_service import (
    calculate_outcome,
    outcome_due_at,
)


def _candle(hour, open_, high, low, close):
    return Candle(
        timestamp=datetime(2026, 8, 3, hour, tzinfo=timezone.utc),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def _decision(trade_allowed=False):
    return {
        "signal_timestamp": "2026-08-03T08:00:00+00:00",
        "target_horizon_bars": 3,
        "target_min_net_return": 0.002,
        "target_max_drawdown": -0.015,
        "trade_allowed": trade_allowed,
    }


def test_outcome_due_at_includes_signal_close_and_future_horizon():
    assert outcome_due_at(
        "2026-08-03T08:00:00+00:00",
        "1h",
        3,
    ) == "2026-08-03T12:00:00+00:00"


def test_calculate_successful_false_negative(monkeypatch):
    monkeypatch.setattr(settings, "OUTCOME_FEE", 0.0)
    monkeypatch.setattr(settings, "OUTCOME_SLIPPAGE", 0.0)
    result = calculate_outcome(
        decision=_decision(trade_allowed=False),
        candles=[
            _candle(8, 100, 101, 99, 100),
            _candle(9, 100, 101, 99.5, 100.5),
            _candle(10, 100.5, 102, 100, 101.5),
            _candle(11, 101.5, 103, 101, 102.5),
        ],
    )
    assert result.actual_target is True
    assert result.prediction_correct is False
    assert result.realized_entry_price == 100
    assert result.realized_exit_price == 102.5
    assert result.realized_max_drawdown == pytest.approx(-0.005)


def test_calculate_outcome_requires_full_horizon():
    with pytest.raises(ValueError, match="not enough closed candles"):
        calculate_outcome(
            decision=_decision(),
            candles=[
                _candle(9, 100, 101, 99, 100),
                _candle(10, 100, 101, 99, 100),
            ],
        )

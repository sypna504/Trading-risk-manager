from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import ModuleType

import pytest

# outcome_service imports market_services, whose network adapter imports ccxt.
# The pure outcome math does not need ccxt, so provide an import-only stub when
# the optional dependency is absent in this execution environment.
if "ccxt" not in sys.modules:
    try:
        import ccxt  # noqa: F401
    except ImportError:
        fake = ModuleType("ccxt")
        fake.binance = lambda *args, **kwargs: None
        fake.bybit = lambda *args, **kwargs: None
        sys.modules["ccxt"] = fake

from app.backend.api.app.services.market_services import Candle
from app.backend.api.app.services.outcome_service import (
    OutcomeDataGapError,
    calculate_outcome,
)


def candle(hour: int, *, low=99.0, high=101.0, close=100.0) -> Candle:
    return Candle(
        timestamp=datetime(2026, 1, 1, hour, tzinfo=timezone.utc),
        open=100.0,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


def decision() -> dict:
    return {
        "signal_timestamp": "2026-01-01T08:00:00+00:00",
        "interval": "1h",
        "target_horizon_bars": 3,
        "target_definition": "horizon_return_drawdown",
        "target_min_net_return": -1.0,
        "target_max_drawdown": -1.0,
        "target_fee": 0.0,
        "target_slippage": 0.0,
        "trade_allowed": True,
    }


def test_outcome_accepts_exact_anchored_future_window():
    result = calculate_outcome(
        decision=decision(),
        candles=[candle(9), candle(10), candle(11)],
        now=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    assert result.realized_holding_bars == 3


def test_outcome_rejects_wrong_late_window_even_with_enough_candles():
    with pytest.raises(OutcomeDataGapError, match="anchored"):
        calculate_outcome(
            decision=decision(),
            candles=[candle(20), candle(21), candle(22)],
            now=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
        )

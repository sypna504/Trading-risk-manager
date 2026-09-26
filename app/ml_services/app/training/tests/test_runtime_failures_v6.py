from __future__ import annotations

from types import SimpleNamespace

import grpc
import pytest

from app.config import Settings
from app.features_builder import MIN_CANDLES
from app.online.validation import Validator


class AbortCalled(RuntimeError):
    def __init__(self, code, details):
        super().__init__(details)
        self.code = code
        self.details = details


class FakeContext:
    def abort(self, code, details):
        raise AbortCalled(code, details)


def _request(candles_count: int = MIN_CANDLES):
    candle = SimpleNamespace(
        timestamp_ms=1,
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.0,
        volume=10.0,
    )
    return SimpleNamespace(
        symbol="BTCUSDT",
        interval="1h",
        strategy_name="mean_reversion",
        candles=[candle for _ in range(candles_count)],
    )


def test_ml_settings_has_min_candles():
    settings = Settings(_env_file=None)
    assert settings.MIN_CANDLES == MIN_CANDLES == 60


def test_validator_uses_defined_minimum_candles():
    Validator(FakeContext(), _request()).validate_candles_count()
    with pytest.raises(AbortCalled) as error:
        Validator(FakeContext(), _request(MIN_CANDLES - 1)).validate_candles_count()
    assert error.value.code == grpc.StatusCode.INVALID_ARGUMENT
    assert "at least 60" in error.value.details

from types import SimpleNamespace

import grpc
import pytest

from app.ml_services.app.config import settings
from app.ml_services.app.online.validation import Validator


class AbortError(Exception):
    pass


class Context:
    def abort(self, code, details):
        raise AbortError((code, details))


def _candle(**overrides):
    values = {
        "timestamp_ms": 1,
        "open": 1.0,
        "high": 2.0,
        "low": 0.5,
        "close": 1.5,
        "volume": 1.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _request(candles):
    return SimpleNamespace(
        symbol="BTCUSDT",
        interval="1h",
        strategy_name="breakout",
        candles=candles,
    )


def test_validator_rejects_nan_ohlcv(monkeypatch):
    monkeypatch.setattr(settings, "MIN_CANDLES", 1)
    with pytest.raises(AbortError) as captured:
        Validator(Context(), _request([_candle(close=float("nan"))])).validate()
    assert captured.value.args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
    assert "finite" in captured.value.args[0][1]


def test_validator_uses_configured_minimum(monkeypatch):
    monkeypatch.setattr(settings, "MIN_CANDLES", 2)
    with pytest.raises(AbortError) as captured:
        Validator(Context(), _request([_candle()])).validate()
    assert "at least 2" in captured.value.args[0][1]

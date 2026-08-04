from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.backend.api.app.services.market_services import Candle
from app.backend.api.app.services import signal_service
from app.ml_services.app.features_builder import latest_complete_feature_row


def test_latest_complete_feature_row_never_falls_back_to_stale_row():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "close": [100.0, 101.0],
            "required": [1.0, float("nan")],
        }
    )
    with pytest.raises(ValueError, match="latest candle"):
        latest_complete_feature_row(frame, ["timestamp", "close", "required"])


def test_signal_service_rejects_incomplete_latest_row(monkeypatch):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(start + timedelta(hours=i), 100, 102, 98, 101, 10)
        for i in range(60)
    ]
    columns = {
        "timestamp": [start, start + timedelta(hours=1)],
        "symbol": ["BTCUSDT", "BTCUSDT"],
        "close": [100.0, 101.0],
        "atr_14_pct": [0.01, float("nan")],
        "rsi_14": [40.0, 40.0],
        "price_z_20": [0.0, 0.0],
        "volume_z_20": [0.0, 0.0],
        "high_20": [99.0, 100.0],
        "signal_breakout": [1, 0],
        "signal_mean_reversion": [0, 0],
    }
    monkeypatch.setattr(
        signal_service,
        "calculate_features",
        lambda _frame: pd.DataFrame(columns),
    )
    with pytest.raises(ValueError, match="latest candle"):
        signal_service.detect_trading_signal(candles, "BTCUSDT")

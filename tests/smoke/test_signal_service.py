from datetime import datetime, timedelta, timezone

import pandas as pd

from app.backend.api.app.services.market_services import Candle
from app.backend.api.app.services import signal_service


def _candles(count=60):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            timestamp=start + timedelta(hours=index),
            open=100,
            high=102,
            low=98,
            close=101,
            volume=10,
        )
        for index in range(count)
    ]


def test_no_signal(monkeypatch):
    frame = pd.DataFrame(
        [
            {
                "timestamp": "2026-01-03T12:00:00",
                "symbol": "BTCUSDT",
                "close": 100.0,
                "atr_14_pct": 0.01,
                "rsi_14": 50.0,
                "price_z_20": 0.0,
                "volume_z_20": 0.0,
                "high_20": 105.0,
                "signal_breakout": 0,
                "signal_mean_reversion": 0,
            }
        ]
    )
    monkeypatch.setattr(signal_service, "calculate_features", lambda _: frame)

    result = signal_service.detect_trading_signal(_candles(), "BTCUSDT")

    assert result["signal_detected"] is False
    assert result["active_strategies"] == []

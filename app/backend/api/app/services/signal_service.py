from __future__ import annotations

from typing import Any

import pandas as pd

from app.ml_services.app.features_builder import (
    calculate_features,
    latest_complete_feature_row,
)

from ..config import settings
from .market_services import Candle


REQUIRED_SIGNAL_COLUMNS = [
    "timestamp",
    "close",
    "atr_14_pct",
    "rsi_14",
    "price_z_20",
    "volume_z_20",
    "high_20",
    "signal_breakout",
    "signal_mean_reversion",
]


def detect_trading_signal(
    candles: list[Candle],
    symbol: str,
) -> dict[str, Any]:
    if len(candles) < settings.MIN_CANDLES:
        raise ValueError(
            f"at least {settings.MIN_CANDLES} candles are required, "
            f"received {len(candles)}"
        )

    candles_df = pd.DataFrame(
        [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "symbol": symbol,
            }
            for candle in candles
        ]
    )

    features = calculate_features(candles_df)
    latest_frame = latest_complete_feature_row(
        features,
        REQUIRED_SIGNAL_COLUMNS,
    )
    latest = latest_frame.iloc[0]
    active_strategies: list[str] = []

    if int(latest["signal_breakout"]) == 1:
        active_strategies.append("breakout")

    if int(latest["signal_mean_reversion"]) == 1:
        active_strategies.append("mean_reversion")

    signal_detected = bool(active_strategies)
    reason = (
        "active signal: " + ", ".join(active_strategies)
        if signal_detected
        else "breakout and mean_reversion conditions are not met"
    )

    return {
        "signal_detected": signal_detected,
        "active_strategies": active_strategies,
        "timestamp": pd.Timestamp(latest["timestamp"]).isoformat(),
        "symbol": str(latest["symbol"]),
        "close": float(latest["close"]),
        "atr_14_pct": float(latest["atr_14_pct"]),
        "signal_breakout": int(latest["signal_breakout"]),
        "signal_mean_reversion": int(latest["signal_mean_reversion"]),
        "indicators": {
            "rsi_14": float(latest["rsi_14"]),
            "price_z_20": float(latest["price_z_20"]),
            "volume_z_20": float(latest["volume_z_20"]),
            "high_20": float(latest["high_20"]),
        },
        "reason": reason,
    }

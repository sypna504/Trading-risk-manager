from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.features_builder import (
    CAT_FEATURES,
    FEATURE_COLUMNS,
    MIN_CANDLES,
    build_inference_features,
    calculate_features,
    calculate_symbol_features,
    normalize_symbol,
    rolling_zscore,
)


def _candles(rows: int = 80) -> pd.DataFrame:
    timestamp = pd.date_range("2026-01-01", periods=rows, freq="h")
    close = 100 + np.sin(np.arange(rows) / 5) + np.arange(rows) * 0.05
    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1000 + np.arange(rows) * 10,
            "symbol": ["BTCUSDT"] * rows,
        }
    )


def test_normalize_symbol():
    assert normalize_symbol(" btc/usdt ") == "BTCUSDT"
    assert normalize_symbol("eth-usdt") == "ETHUSDT"


def test_rolling_zscore():
    result = rolling_zscore(pd.Series([1, 2, 3, 4, 5], dtype=float), 3)
    assert result.iloc[:2].isna().all()
    assert np.isfinite(result.iloc[-1])


def test_calculate_symbol_features():
    result = calculate_symbol_features(_candles())
    assert "ret_1" in result
    assert "signal_breakout" in result
    assert result["high_20"].iloc[:20].isna().all()
    assert set(result["hour"].dropna().unique()).issubset({str(i) for i in range(24)})


def test_calculate_features_multiple_symbols_and_missing_column():
    first = _candles()
    second = _candles().assign(symbol="ETH/USDT", close=lambda frame: frame["close"] + 10)
    result = calculate_features(pd.concat([first, second], ignore_index=True))
    assert set(result["symbol"]) == {"BTCUSDT", "ETHUSDT"}
    with pytest.raises(ValueError, match="missing candle columns"):
        calculate_features(first.drop(columns=["volume"]))


def test_build_inference_features_success_and_errors():
    candles = _candles().drop(columns=["symbol"]).to_dict("records")
    result = build_inference_features(candles, "btc/usdt", "breakout")
    assert list(result.columns) == FEATURE_COLUMNS
    assert result.iloc[0]["symbol"] == "BTCUSDT"
    assert result.iloc[0]["strategy_name"] == "breakout"
    assert all(result[column].dtype == object for column in CAT_FEATURES)

    with pytest.raises(ValueError, match="at least"):
        build_inference_features(candles[: MIN_CANDLES - 1], "BTCUSDT", "breakout")

    flat = _candles().drop(columns=["symbol"]).assign(close=100, open=100, high=100, low=100)
    with pytest.raises(ValueError, match="complete feature row"):
        build_inference_features(flat.to_dict("records"), "BTCUSDT", "breakout")

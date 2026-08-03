from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.training.data_validation import (
    find_time_gaps,
    interval_to_timedelta,
    normalize_history_frame,
    validate_dataset,
    validate_history,
)


def test_interval_to_timedelta_supported_and_invalid():
    assert interval_to_timedelta("15m") == pd.Timedelta(minutes=15)
    assert interval_to_timedelta("1h") == pd.Timedelta(hours=1)
    assert interval_to_timedelta("2d") == pd.Timedelta(days=2)
    assert interval_to_timedelta("1w") == pd.Timedelta(weeks=1)
    with pytest.raises(ValueError, match="unsupported interval"):
        interval_to_timedelta("1s")


def test_normalize_history_frame_normalizes_and_sorts(history_frame):
    frame = history_frame.iloc[[3, 0, 2, 1]].copy()
    frame["symbol"] = frame["symbol"].str.replace("USDT", "/USDT")
    frame[["open", "high", "low", "close", "volume"]] = frame[
        ["open", "high", "low", "close", "volume"]
    ].astype(str)
    result = normalize_history_frame(frame)
    assert result["timestamp"].dt.tz is not None
    assert result["symbol"].str.contains("/").sum() == 0
    assert result.equals(result.sort_values(["symbol", "timestamp"]).reset_index(drop=True))


def test_normalize_history_frame_rejects_missing_column(history_frame):
    with pytest.raises(ValueError, match="missing history columns"):
        normalize_history_frame(history_frame.drop(columns=["volume"]))


def test_find_time_gaps_reports_missing_bars(history_frame):
    frame = history_frame[history_frame["symbol"] == "BTCUSDT"].iloc[:5].drop(index=2)
    gaps = find_time_gaps(frame, "1h")
    assert "BTCUSDT" in gaps
    assert gaps["BTCUSDT"][0]["missing_bars"] == 1


def test_validate_history_accepts_valid_data_and_warns_on_gap(history_frame):
    frame = history_frame.groupby("symbol", group_keys=False).head(5)
    result = validate_history(
        frame,
        allowed_symbols=["BTCUSDT", "ETHUSDT"],
        interval="1h",
        closed_candle_cutoff=pd.Timestamp("2026-01-02T00:00:00Z"),
        minimum_rows_per_symbol=2,
    )
    assert result.valid
    assert result.report["duplicate_count"] == 0


def test_validate_history_detects_all_core_failures(history_frame):
    frame = history_frame.groupby("symbol", group_keys=False).head(2).copy()
    duplicate = frame.iloc[[0]].copy()
    frame = pd.concat([frame, duplicate], ignore_index=True)
    frame.loc[0, "open"] = -1
    frame.loc[1, "volume"] = -1
    frame.loc[2, "high"] = frame.loc[2, "low"] - 1
    frame.loc[3, "low"] = frame.loc[3, "high"] + 1
    frame.loc[4, "close"] = np.inf
    frame.loc[0, "symbol"] = "UNKNOWNUSDT"
    result = validate_history(
        frame,
        allowed_symbols=["BTCUSDT", "ETHUSDT"],
        interval="1h",
        closed_candle_cutoff=pd.Timestamp("2025-12-31T23:00:00Z"),
        minimum_rows_per_symbol=3,
    )
    assert not result.valid
    assert result.report["unknown_symbols"] == ["UNKNOWNUSDT"]
    assert result.report["inf_count"] == 1
    assert result.report["unclosed_candle_count"] > 0
    assert result.report["errors"]


def test_validate_history_handles_missing_schema():
    result = validate_history(
        pd.DataFrame({"timestamp": []}),
        allowed_symbols=[],
        interval="1h",
    )
    assert not result.valid
    assert "missing history columns" in result.report["errors"][0]


def test_validate_dataset_valid_and_invalid(model_frame):
    valid = validate_dataset(model_frame, minimum_rows=10, minimum_class_rows=2)
    assert valid.valid
    assert valid.report["class_counts"] == {"0": 120, "1": 120}

    invalid = model_frame.iloc[:3].copy()
    invalid.loc[:, "target_good_trade"] = 1
    invalid.loc[invalid.index[0], "net_return"] = np.inf
    invalid = pd.concat([invalid, invalid.iloc[[0]]], ignore_index=True)
    result = validate_dataset(invalid, minimum_rows=10, minimum_class_rows=2)
    assert not result.valid
    assert result.report["errors"]


def test_validate_dataset_missing_columns():
    result = validate_dataset(pd.DataFrame({"timestamp": []}), 1, 1)
    assert not result.valid
    assert "missing dataset columns" in result.report["errors"][0]

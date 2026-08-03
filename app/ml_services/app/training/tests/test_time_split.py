from __future__ import annotations

import pandas as pd

from app.training.time_split import global_time_split


def _dataset() -> pd.DataFrame:
    rows = []
    for timestamp in pd.date_range("2026-01-01", periods=100, freq="h"):
        for symbol in ("BTCUSDT", "ETHUSDT"):
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "strategy_name": "breakout",
                    "target_good_trade": int(timestamp.hour % 2 == 0),
                }
            )
    return pd.DataFrame(rows)


def test_global_split_has_no_timestamp_overlap_and_purge():
    split = global_time_split(_dataset(), 0.7, 0.15, 0.15, purge_bars=3)
    train_times = set(split.train["timestamp"])
    valid_times = set(split.validation["timestamp"])
    test_times = set(split.test["timestamp"])
    assert not train_times & valid_times
    assert not train_times & test_times
    assert not valid_times & test_times
    assert max(train_times) < min(valid_times)
    assert max(valid_times) < min(test_times)


def test_rolling_window_moves_with_latest_timestamp():
    from app.training.time_split import rolling_window_bounds

    first_start, _ = rolling_window_bounds(
        pd.Timestamp("2026-08-01T00:00:00Z"), 180, pd.Timedelta(hours=1)
    )
    second_start, _ = rolling_window_bounds(
        pd.Timestamp("2026-08-02T00:00:00Z"), 180, pd.Timedelta(hours=1)
    )
    assert second_start - first_start == pd.Timedelta(days=1)

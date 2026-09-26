from __future__ import annotations

import pandas as pd

from app.training.data_validation import validate_history
from app.training.update_history import last_closed_open_time, merge_history


def _frame(timestamp: str, close: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 10.0,
                "symbol": "BTCUSDT",
            }
        ]
    )


def test_merge_history_is_idempotent_and_keeps_fresh_copy():
    old = _frame("2026-08-01T10:00:00Z", close=100)
    new = _frame("2026-08-01T10:00:00Z", close=101)
    merged = merge_history(old, new)
    assert len(merged) == 1
    assert merged.iloc[0]["close"] == 101
    merged_again = merge_history(merged, new)
    assert len(merged_again) == 1


def test_current_unclosed_candle_is_excluded_by_cutoff():
    cutoff = last_closed_open_time(pd.Timestamp("2026-08-02T19:02:00Z"), "1h")
    assert cutoff == pd.Timestamp("2026-08-02T18:00:00Z")


def test_validation_detects_duplicate_timestamp():
    frame = pd.concat([_frame("2026-08-01T10:00:00Z")] * 2, ignore_index=True)
    result = validate_history(
        frame,
        allowed_symbols=["BTCUSDT"],
        interval="1h",
        closed_candle_cutoff=pd.Timestamp("2026-08-01T11:00:00Z"),
    )
    assert not result.valid
    assert result.report["duplicate_count"] == 1

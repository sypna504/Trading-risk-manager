from __future__ import annotations

import pandas as pd
import pytest

from app.training.time_split import (
    _take_by_timestamps,
    expanding_walk_forward_splits,
    global_time_split,
    rolling_window_bounds,
    walk_forward_time_splits,
)


def test_take_by_timestamps(model_frame):
    timestamps = pd.Index(model_frame["timestamp"].drop_duplicates().iloc[:2])
    result = _take_by_timestamps(model_frame, timestamps)
    assert set(result["timestamp"]) == set(timestamps)


def test_global_time_split_success_and_errors(model_frame):
    result = global_time_split(model_frame, 0.7, 0.15, 0.15, purge_bars=3)
    assert not result.train.empty
    assert max(result.train["timestamp"]) < min(result.validation["timestamp"])
    assert max(result.validation["timestamp"]) < min(result.test["timestamp"])
    assert result.metadata["purge_bars"] == 3

    with pytest.raises(ValueError, match="sum to 1"):
        global_time_split(model_frame, 0.8, 0.15, 0.15, 3)
    with pytest.raises(ValueError, match="not enough unique timestamps"):
        global_time_split(model_frame.head(10), 0.7, 0.15, 0.15, 3)


def test_expanding_walk_forward_splits(model_frame):
    folds = expanding_walk_forward_splits(model_frame, folds=3, minimum_fold_rows=5, purge_bars=2)
    assert len(folds) == 3
    for train, validation in folds:
        assert max(train["timestamp"]) < min(validation["timestamp"])
    assert expanding_walk_forward_splits(model_frame, folds=0, minimum_fold_rows=1, purge_bars=1) == []


def test_walk_forward_time_splits(model_frame):
    folds = walk_forward_time_splits(model_frame, folds=2, minimum_fold_rows=5, purge_bars=2)
    assert len(folds) == 2
    for train, validation, test in folds:
        assert max(train["timestamp"]) < min(validation["timestamp"])
        assert max(validation["timestamp"]) < min(test["timestamp"])
    assert walk_forward_time_splits(model_frame.head(10), 2, 1, 1) == []


def test_rolling_window_bounds():
    window, warmup = rolling_window_bounds(
        pd.Timestamp("2026-08-01T00:00:00Z"),
        180,
        pd.Timedelta(hours=1),
        warmup_bars=24,
    )
    assert window == pd.Timestamp("2026-02-02T00:00:00Z")
    assert warmup == window - pd.Timedelta(hours=24)

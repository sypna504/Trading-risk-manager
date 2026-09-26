from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class TimeSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    metadata: dict


def _take_by_timestamps(df: pd.DataFrame, timestamps: pd.Index) -> pd.DataFrame:
    return df[df["timestamp"].isin(timestamps)].copy()


def _purged_before(
    timestamps: pd.Index,
    boundary: pd.Timestamp,
    purge_timedelta: pd.Timedelta | None,
    fallback_bars: int,
) -> pd.Index:
    if purge_timedelta is not None:
        return timestamps[timestamps < boundary - purge_timedelta]
    boundary_position = int(timestamps.searchsorted(boundary, side="left"))
    return timestamps[: max(boundary_position - fallback_bars, 0)]


def global_time_split(
    dataset: pd.DataFrame,
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    purge_bars: int = 0,
    purge_timedelta: pd.Timedelta | None = None,
) -> TimeSplit:
    if abs(train_ratio + validation_ratio + test_ratio - 1.0) > 1e-8:
        raise ValueError("split ratios must sum to 1")

    df = dataset.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    sort_columns = [column for column in ["timestamp", "symbol", "strategy_name", "interval"] if column in df.columns]
    df = df.sort_values(sort_columns).reset_index(drop=True)
    timestamps = pd.Index(df["timestamp"].drop_duplicates().sort_values())
    if len(timestamps) < 20:
        raise ValueError("not enough unique timestamps for time split")

    train_boundary_index = int(len(timestamps) * train_ratio)
    validation_boundary_index = int(len(timestamps) * (train_ratio + validation_ratio))
    if train_boundary_index <= 0 or validation_boundary_index >= len(timestamps):
        raise ValueError("invalid time split boundaries")

    validation_start = timestamps[train_boundary_index]
    test_start = timestamps[validation_boundary_index]
    train_times = _purged_before(
        timestamps,
        validation_start,
        purge_timedelta,
        purge_bars,
    )
    validation_candidates = timestamps[
        (timestamps >= validation_start) & (timestamps < test_start)
    ]
    if purge_timedelta is not None:
        validation_times = validation_candidates[
            validation_candidates < test_start - purge_timedelta
        ]
    else:
        validation_times = validation_candidates[: max(len(validation_candidates) - purge_bars, 0)]
    test_times = timestamps[timestamps >= test_start]

    train = _take_by_timestamps(df, train_times)
    validation = _take_by_timestamps(df, validation_times)
    test = _take_by_timestamps(df, test_times)
    if train.empty or validation.empty or test.empty:
        raise ValueError("one of train/validation/test splits is empty")

    sets = [set(part["timestamp"].unique()) for part in (train, validation, test)]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise AssertionError("timestamp leakage between splits")
    if purge_timedelta is not None:
        if train["timestamp"].max() >= validation["timestamp"].min() - purge_timedelta:
            raise AssertionError("physical purge gap between train and validation is missing")
        if validation["timestamp"].max() >= test["timestamp"].min() - purge_timedelta:
            raise AssertionError("physical purge gap between validation and test is missing")

    metadata = {
        "train_start": str(train["timestamp"].min()),
        "train_end": str(train["timestamp"].max()),
        "validation_start": str(validation["timestamp"].min()),
        "validation_end": str(validation["timestamp"].max()),
        "test_start": str(test["timestamp"].min()),
        "test_end": str(test["timestamp"].max()),
        "train_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "purge_bars": purge_bars,
        "purge_timedelta": str(purge_timedelta) if purge_timedelta is not None else None,
    }
    return TimeSplit(train, validation, test, metadata)


def expanding_walk_forward_splits(
    dataset: pd.DataFrame,
    folds: int,
    minimum_fold_rows: int,
    purge_bars: int = 0,
    purge_timedelta: pd.Timedelta | None = None,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    df = dataset.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    timestamps = pd.Index(df["timestamp"].drop_duplicates().sort_values())
    if folds < 1:
        return []

    block = max(len(timestamps) // (folds + 1), 1)
    results: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    for fold in range(folds):
        validation_start_index = block * (fold + 1)
        validation_end = block * (fold + 2) if fold < folds - 1 else len(timestamps)
        if validation_start_index >= len(timestamps):
            break
        boundary = timestamps[validation_start_index]
        train_times = _purged_before(timestamps, boundary, purge_timedelta, purge_bars)
        validation_times = timestamps[validation_start_index:validation_end]
        train = _take_by_timestamps(df, train_times)
        validation = _take_by_timestamps(df, validation_times)
        if len(train) >= minimum_fold_rows and len(validation) >= minimum_fold_rows:
            results.append((train, validation))
    return results


def walk_forward_time_splits(
    dataset: pd.DataFrame,
    folds: int,
    minimum_fold_rows: int,
    purge_bars: int = 0,
    purge_timedelta: pd.Timedelta | None = None,
) -> list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """Expanding train with independent validation and test blocks per fold."""
    df = dataset.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    timestamps = pd.Index(df["timestamp"].drop_duplicates().sort_values())
    if folds < 1 or len(timestamps) < 30:
        return []

    initial_train_end = max(int(len(timestamps) * 0.40), 2)
    remaining = len(timestamps) - initial_train_end
    block = remaining // (2 * folds)
    if block < 2:
        return []

    results: list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    for fold in range(folds):
        validation_start_index = initial_train_end + 2 * fold * block
        validation_end_index = validation_start_index + block
        test_start_index = validation_end_index
        test_end_index = min(test_start_index + block, len(timestamps))
        if test_start_index >= len(timestamps):
            break

        validation_start = timestamps[validation_start_index]
        test_start = timestamps[test_start_index]
        train_times = _purged_before(
            timestamps,
            validation_start,
            purge_timedelta,
            purge_bars,
        )
        validation_candidates = timestamps[validation_start_index:validation_end_index]
        if purge_timedelta is not None:
            validation_times = validation_candidates[
                validation_candidates < test_start - purge_timedelta
            ]
        else:
            validation_times = validation_candidates[: max(len(validation_candidates) - purge_bars, 0)]
        test_times = timestamps[test_start_index:test_end_index]

        train = _take_by_timestamps(df, train_times)
        validation = _take_by_timestamps(df, validation_times)
        test = _take_by_timestamps(df, test_times)
        if (
            len(train) >= minimum_fold_rows
            and len(validation) >= minimum_fold_rows
            and len(test) >= minimum_fold_rows
        ):
            results.append((train, validation, test))
    return results


def rolling_window_bounds(
    last_timestamp: pd.Timestamp,
    training_window_days: int,
    interval_delta: pd.Timedelta,
    warmup_bars: int = 250,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    end = pd.to_datetime(last_timestamp, utc=True)
    window_start = end - pd.Timedelta(days=training_window_days)
    warmup_start = window_start - warmup_bars * interval_delta
    return window_start, warmup_start

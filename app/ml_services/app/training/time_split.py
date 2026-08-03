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


def global_time_split(
    dataset: pd.DataFrame,
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    purge_bars: int,
) -> TimeSplit:
    if abs(train_ratio + validation_ratio + test_ratio - 1.0) > 1e-8:
        raise ValueError("split ratios must sum to 1")

    df = dataset.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["timestamp", "symbol", "strategy_name"]).reset_index(drop=True)
    timestamps = pd.Index(df["timestamp"].drop_duplicates().sort_values())
    if len(timestamps) < 20:
        raise ValueError("not enough unique timestamps for time split")

    train_boundary = int(len(timestamps) * train_ratio)
    validation_boundary = int(len(timestamps) * (train_ratio + validation_ratio))

    train_times = timestamps[: max(train_boundary - purge_bars, 0)]
    validation_times = timestamps[train_boundary : max(validation_boundary - purge_bars, train_boundary)]
    test_times = timestamps[validation_boundary:]

    train = _take_by_timestamps(df, train_times)
    validation = _take_by_timestamps(df, validation_times)
    test = _take_by_timestamps(df, test_times)

    if train.empty or validation.empty or test.empty:
        raise ValueError("one of train/validation/test splits is empty")

    sets = [set(part["timestamp"].unique()) for part in (train, validation, test)]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise AssertionError("timestamp leakage between splits")

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
    }
    return TimeSplit(train, validation, test, metadata)


def expanding_walk_forward_splits(
    dataset: pd.DataFrame,
    folds: int,
    minimum_fold_rows: int,
    purge_bars: int,
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
        validation_start = block * (fold + 1)
        validation_end = block * (fold + 2) if fold < folds - 1 else len(timestamps)
        train_times = timestamps[: max(validation_start - purge_bars, 0)]
        validation_times = timestamps[validation_start:validation_end]
        train = _take_by_timestamps(df, train_times)
        validation = _take_by_timestamps(df, validation_times)
        if len(train) >= minimum_fold_rows and len(validation) >= minimum_fold_rows:
            results.append((train, validation))
    return results


def walk_forward_time_splits(
    dataset: pd.DataFrame,
    folds: int,
    minimum_fold_rows: int,
    purge_bars: int,
) -> list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """Expanding train with independent validation and test blocks per fold."""
    df = dataset.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    timestamps = pd.Index(df["timestamp"].drop_duplicates().sort_values())
    if folds < 1 or len(timestamps) < 30:
        return []

    initial_train_end = max(int(len(timestamps) * 0.40), purge_bars + 1)
    remaining = len(timestamps) - initial_train_end
    block = remaining // (2 * folds)
    if block <= purge_bars:
        return []

    results: list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    for fold in range(folds):
        validation_start = initial_train_end + 2 * fold * block
        validation_end = validation_start + block
        test_start = validation_end
        test_end = test_start + block if fold < folds - 1 else min(test_start + block, len(timestamps))
        if test_start >= len(timestamps):
            break

        train_times = timestamps[: max(validation_start - purge_bars, 0)]
        validation_times = timestamps[
            validation_start : max(validation_end - purge_bars, validation_start)
        ]
        test_times = timestamps[test_start:test_end]

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

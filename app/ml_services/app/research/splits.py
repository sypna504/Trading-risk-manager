from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class ResearchSplit:
    train: pd.DataFrame
    model_selection: pd.DataFrame
    calibration_fit: pd.DataFrame
    calibration_selection: pd.DataFrame
    threshold_selection: pd.DataFrame
    development_oos: pd.DataFrame
    final_holdout: pd.DataFrame
    metadata: dict


def _slice(df: pd.DataFrame, timestamps: pd.Index) -> pd.DataFrame:
    return df[df["timestamp"].isin(timestamps)].copy()


def _before_with_purge(timestamps: pd.Index, boundary: pd.Timestamp, purge: pd.Timedelta) -> pd.Index:
    return timestamps[timestamps < boundary - purge]


def _partition_times(timestamps: pd.Index, fractions: list[float]) -> list[pd.Index]:
    if any(value <= 0 for value in fractions) or abs(sum(fractions) - 1.0) > 1e-8:
        raise ValueError("partition fractions must be positive and sum to 1")
    edges = [0]
    cumulative = 0.0
    for fraction in fractions[:-1]:
        cumulative += fraction
        edges.append(int(len(timestamps) * cumulative))
    edges.append(len(timestamps))
    return [timestamps[start:end] for start, end in zip(edges[:-1], edges[1:])]


def split_research_dataset(
    frame: pd.DataFrame,
    *,
    final_holdout_days: int,
    purge: pd.Timedelta,
) -> ResearchSplit:
    df = frame.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values([column for column in ["timestamp", "symbol", "strategy_name"] if column in df.columns]).reset_index(drop=True)
    if df.empty:
        raise ValueError("research dataset is empty")
    max_ts = df["timestamp"].max()
    holdout_start = max_ts - pd.Timedelta(days=final_holdout_days)
    development = df[df["timestamp"] < holdout_start - purge].copy()
    final_holdout = df[df["timestamp"] >= holdout_start].copy()
    if development.empty or final_holdout.empty:
        raise ValueError("development or final holdout is empty")
    times = pd.Index(development["timestamp"].drop_duplicates().sort_values())
    if len(times) < 60:
        raise ValueError("not enough unique timestamps for research split")
    # Final holdout never participates in model/target/feature/hyperparameter selection.
    raw_parts = _partition_times(times, [0.55, 0.12, 0.08, 0.07, 0.08, 0.10])
    parts: list[pd.DataFrame] = []
    for index, selected in enumerate(raw_parts):
        if index < len(raw_parts) - 1:
            next_start = raw_parts[index + 1][0]
            selected = selected[selected < next_start - purge]
        part = _slice(development, selected)
        if part.empty:
            raise ValueError("research partition empty after purge")
        parts.append(part)
    names = ["train", "model_selection", "calibration_fit", "calibration_selection", "threshold_selection", "development_oos"]
    metadata = {
        "holdout_start": str(holdout_start),
        "purge": str(purge),
        "parts": {
            name: {
                "rows": int(len(part)),
                "start": str(part["timestamp"].min()),
                "end": str(part["timestamp"].max()),
            }
            for name, part in zip(names, parts)
        },
        "final_holdout": {
            "rows": int(len(final_holdout)),
            "start": str(final_holdout["timestamp"].min()),
            "end": str(final_holdout["timestamp"].max()),
        },
    }
    return ResearchSplit(*parts, final_holdout=final_holdout, metadata=metadata)


def split_walk_forward_fold(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    *,
    purge: pd.Timedelta,
) -> ResearchSplit:
    """Adapt a production walk-forward fold to the research selection sequence."""
    val = validation.copy()
    val["timestamp"] = pd.to_datetime(val["timestamp"])
    times = pd.Index(val["timestamp"].drop_duplicates().sort_values())
    if len(times) < 16:
        raise ValueError("walk-forward validation block is too short")
    raw = _partition_times(times, [0.35, 0.20, 0.15, 0.30])
    parts: list[pd.DataFrame] = []
    for index, selected in enumerate(raw):
        if index < len(raw) - 1:
            next_start = raw[index + 1][0]
            selected = selected[selected < next_start - purge]
        part = _slice(val, selected)
        if part.empty:
            raise ValueError("walk-forward sub-partition empty after purge")
        parts.append(part)
    # model_selection, calibration_fit, calibration_selection and threshold_selection
    # are the four chronological validation sub-blocks. The fold's test remains untouched.
    return ResearchSplit(
        train=train.copy(),
        model_selection=parts[0],
        calibration_fit=parts[1],
        calibration_selection=parts[2],
        threshold_selection=parts[3],
        development_oos=test.copy(),
        final_holdout=test.iloc[0:0].copy(),
        metadata={
            "walk_forward": True,
            "train_start": str(train["timestamp"].min()),
            "train_end": str(train["timestamp"].max()),
            "test_start": str(test["timestamp"].min()),
            "test_end": str(test["timestamp"].max()),
            "purge": str(purge),
        },
    )


def split_deployment_dataset(
    frame: pd.DataFrame,
    *,
    purge: pd.Timedelta,
) -> ResearchSplit:
    """Create a later production-fit sequence after research choices are frozen.

    There is intentionally no OOS claim for this split.  The exact model, target,
    feature set and hyperparameters must already have been selected using the
    separate evaluation holdout before this function is called.
    """
    df = frame.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(
        [column for column in ["timestamp", "symbol", "strategy_name"] if column in df.columns]
    ).reset_index(drop=True)
    times = pd.Index(df["timestamp"].drop_duplicates().sort_values())
    if len(times) < 60:
        raise ValueError("not enough unique timestamps for deployment refit")
    raw = _partition_times(times, [0.73, 0.08, 0.06, 0.05, 0.08])
    parts: list[pd.DataFrame] = []
    for index, selected in enumerate(raw):
        if index < len(raw) - 1:
            next_start = raw[index + 1][0]
            selected = selected[selected < next_start - purge]
        part = _slice(df, selected)
        if part.empty:
            raise ValueError("deployment partition empty after purge")
        parts.append(part)
    train, model_selection, calibration_fit, calibration_selection, threshold_selection = parts
    return ResearchSplit(
        train=train,
        model_selection=model_selection,
        calibration_fit=calibration_fit,
        calibration_selection=calibration_selection,
        threshold_selection=threshold_selection,
        development_oos=threshold_selection.iloc[0:0].copy(),
        final_holdout=threshold_selection.iloc[0:0].copy(),
        metadata={
            "production_refit": True,
            "purge": str(purge),
            "parts": {
                name: {
                    "rows": int(len(part)),
                    "start": str(part["timestamp"].min()),
                    "end": str(part["timestamp"].max()),
                }
                for name, part in zip(
                    ["train", "model_selection", "calibration_fit", "calibration_selection", "threshold_selection"],
                    parts,
                )
            },
        },
    )

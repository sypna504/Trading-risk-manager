from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..features_builder import FEATURE_COLUMNS, calculate_features
from .data_validation import interval_to_timedelta
from .time_split import rolling_window_bounds
from .training_config import TrainingConfig


def _describe(series: pd.Series) -> dict[str, float | None]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"count": 0, "mean": None, "std": None, "min": None, "q25": None, "median": None, "q75": None, "max": None}
    return {
        "count": int(clean.size),
        "mean": float(clean.mean()),
        "std": float(clean.std()) if clean.size > 1 else 0.0,
        "min": float(clean.min()),
        "q25": float(clean.quantile(0.25)),
        "median": float(clean.median()),
        "q75": float(clean.quantile(0.75)),
        "max": float(clean.max()),
    }


def _atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        df.to_parquet(temporary, index=False)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_dataset(
    config: TrainingConfig | None = None,
    raw_df: pd.DataFrame | None = None,
    save: bool = True,
) -> pd.DataFrame:
    config = config or TrainingConfig.from_env()
    source = pd.read_parquet(config.history_path) if raw_df is None else raw_df.copy()
    if source.empty:
        raise ValueError("history is empty")

    source["timestamp"] = pd.to_datetime(source["timestamp"], utc=True)
    source = source.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    source_rows = len(source)
    source_min = source["timestamp"].min()
    source_max = source["timestamp"].max()

    window_start, warmup_start = rolling_window_bounds(
        source_max,
        config.training_window_days,
        interval_to_timedelta(config.interval),
    )
    window_source = source[source["timestamp"] >= warmup_start].copy()

    features = calculate_features(window_source)
    features["timestamp"] = pd.to_datetime(features["timestamp"])
    features = features[features["timestamp"] >= window_start.tz_convert(None)].copy()
    features = features.sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    grouped = features.groupby("symbol", group_keys=False)
    horizon = config.target_horizon
    features["entry_price"] = grouped["open"].shift(-1)
    features["exit_price"] = grouped["close"].shift(-horizon)

    future_lows = [grouped["low"].shift(-step) for step in range(1, horizon + 1)]
    features["future_min_low"] = pd.concat(future_lows, axis=1).min(axis=1)

    round_trip_cost = 2 * (config.fee + config.slippage)
    features["net_return"] = (
        features["exit_price"] / features["entry_price"] - 1 - round_trip_cost
    )
    features["max_drawdown"] = (
        features["future_min_low"] / features["entry_price"] - 1
    )
    features["target_good_trade"] = (
        (features["net_return"] > 0.002)
        & (features["max_drawdown"] > -0.015)
    ).astype(int)

    breakout = features[features["signal_breakout"] == 1].copy()
    breakout["strategy_name"] = "breakout"
    mean_reversion = features[features["signal_mean_reversion"] == 1].copy()
    mean_reversion["strategy_name"] = "mean_reversion"
    dataset = pd.concat([breakout, mean_reversion], ignore_index=True)

    result_columns = [
        "timestamp",
        "entry_price",
        "exit_price",
        "future_min_low",
        "net_return",
        "max_drawdown",
        "target_good_trade",
        *FEATURE_COLUMNS,
    ]
    dataset = dataset[result_columns]
    before_dropna = len(dataset)
    dataset = dataset.replace([np.inf, -np.inf], np.nan)
    dataset = dataset.dropna(
        subset=[
            "entry_price",
            "exit_price",
            "future_min_low",
            "net_return",
            "max_drawdown",
            *FEATURE_COLUMNS,
        ]
    )
    removed_nan = before_dropna - len(dataset)
    dataset = dataset[
        (dataset["entry_price"] > 0)
        & (dataset["exit_price"] > 0)
        & (dataset["future_min_low"] > 0)
    ]
    dataset = dataset.drop_duplicates(
        ["timestamp", "symbol", "strategy_name"], keep="last"
    )
    dataset = dataset.sort_values(["timestamp", "symbol", "strategy_name"]).reset_index(drop=True)

    report = {
        "source_rows": int(source_rows),
        "source_period": {"start": str(source_min), "end": str(source_max)},
        "exchange": config.exchange,
        "interval": config.interval,
        "training_window_days": config.training_window_days,
        "window_period": {
            "start": str(dataset["timestamp"].min()) if not dataset.empty else None,
            "end": str(dataset["timestamp"].max()) if not dataset.empty else None,
        },
        "dataset_rows": int(len(dataset)),
        "symbols": sorted(dataset["symbol"].unique().tolist()) if not dataset.empty else [],
        "strategies": sorted(dataset["strategy_name"].unique().tolist()) if not dataset.empty else [],
        "positive_class_rate": float(dataset["target_good_trade"].mean()) if len(dataset) else 0.0,
        "class_counts": {str(k): int(v) for k, v in dataset["target_good_trade"].value_counts().sort_index().items()},
        "rows_by_strategy": {str(k): int(v) for k, v in dataset.groupby("strategy_name").size().sort_index().items()},
        "rows_by_symbol": {str(k): int(v) for k, v in dataset.groupby("symbol").size().sort_index().items()},
        "removed_nan_rows": int(removed_nan),
        "signal_breakout": int(features["signal_breakout"].sum()),
        "signal_mean_reversion": int(features["signal_mean_reversion"].sum()),
        "net_return": _describe(dataset["net_return"]),
        "max_drawdown": _describe(dataset["max_drawdown"]),
        "fee": config.fee,
        "slippage": config.slippage,
        "target_horizon": config.target_horizon,
    }

    if save:
        _atomic_write_parquet(dataset, config.dataset_path)
        _atomic_write_json(report, config.reports_path / "latest_dataset_report.json")
        print(f"saved dataset: {config.dataset_path}")
        print(f"rows: {len(dataset)}")
    dataset.attrs["dataset_report"] = report
    return dataset


if __name__ == "__main__":
    build_dataset()

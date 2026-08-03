from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.features_builder import CAT_FEATURES, FEATURE_COLUMNS
from app.training.training_config import TrainingConfig


@pytest.fixture
def config(tmp_path: Path) -> TrainingConfig:
    app_dir = tmp_path / "app"
    training_dir = app_dir / "training"
    models_dir = app_dir / "models"
    data_dir = training_dir / "data"
    data_dir.mkdir(parents=True)
    models_dir.mkdir(parents=True)
    return TrainingConfig(
        app_dir=app_dir,
        symbols=["BTCUSDT", "ETHUSDT"],
        interval="1h",
        minimum_history_rows=2,
        minimum_dataset_rows=10,
        minimum_class_rows=2,
        minimum_selected_trades=2,
        minimum_fold_rows=2,
        minimum_new_candles=1,
        minimum_hours_between_retrains=0,
        history_path=data_dir / "history_data.parquet",
        dataset_path=data_dir / "ml_dataset_v2.parquet",
        models_root=models_dir,
        reports_path=models_dir / "reports",
        registry_path=models_dir / "registry.json",
        lock_path=training_dir / ".retrain.lock",
    )


@pytest.fixture
def history_frame() -> pd.DataFrame:
    rows = []
    for symbol_index, symbol in enumerate(("BTCUSDT", "ETHUSDT")):
        for index, timestamp in enumerate(
            pd.date_range("2026-01-01", periods=80, freq="h", tz="UTC")
        ):
            close = 100.0 + symbol_index * 10 + index * 0.1
            rows.append(
                {
                    "timestamp": timestamp,
                    "open": close - 0.05,
                    "high": close + 0.5,
                    "low": close - 0.5,
                    "close": close,
                    "volume": 1000.0 + index,
                    "symbol": symbol,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def model_frame() -> pd.DataFrame:
    rows = []
    timestamps = pd.date_range("2026-01-01", periods=120, freq="h")
    for timestamp_index, timestamp in enumerate(timestamps):
        for symbol_index, symbol in enumerate(("BTCUSDT", "ETHUSDT")):
            target = int((timestamp_index + symbol_index) % 2 == 0)
            row = {
                "timestamp": timestamp,
                "symbol": symbol,
                "strategy_name": (
                    "breakout" if timestamp_index % 2 == 0 else "mean_reversion"
                ),
                "target_good_trade": target,
                "net_return": 0.01 if target else -0.004,
                "max_drawdown": -0.005 if target else -0.02,
                "entry_price": 100.0,
                "exit_price": 101.0 if target else 99.0,
                "future_min_low": 99.5 if target else 97.0,
            }
            for feature_index, column in enumerate(FEATURE_COLUMNS):
                if column in row:
                    continue
                if column in CAT_FEATURES:
                    row[column] = str((timestamp_index + feature_index) % 5)
                else:
                    row[column] = float(
                        np.sin(timestamp_index / 7 + feature_index)
                        + target * 0.2
                        + symbol_index * 0.05
                    )
            rows.append(row)
    return pd.DataFrame(rows)

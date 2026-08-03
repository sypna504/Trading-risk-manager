from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.features_builder import CAT_FEATURES, FEATURE_COLUMNS
from app.training import build_dataset as module
from app.training.build_dataset import (
    _atomic_write_json,
    _atomic_write_parquet,
    _describe,
    build_dataset,
)


def test_describe_empty_and_values():
    assert _describe(pd.Series([None, np.nan]))["count"] == 0
    result = _describe(pd.Series([1, 2, 3]))
    assert result["count"] == 3
    assert result["mean"] == 2.0
    assert result["median"] == 2.0


def test_atomic_write_helpers(monkeypatch, tmp_path):
    json_path = tmp_path / "data.json"
    _atomic_write_json({"value": 1}, json_path)
    assert json.loads(json_path.read_text()) == {"value": 1}

    parquet_path = tmp_path / "data.parquet"

    def fake_to_parquet(self, target, index=False):
        Path(target).write_text("ok", encoding="utf-8")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)
    _atomic_write_parquet(pd.DataFrame({"x": [1]}), parquet_path)
    assert parquet_path.read_text() == "ok"


def _fake_features(source: pd.DataFrame) -> pd.DataFrame:
    result = source.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True).dt.tz_convert(None)
    for index, column in enumerate(FEATURE_COLUMNS):
        if column in result.columns or column == "strategy_name":
            continue
        if column in CAT_FEATURES:
            result[column] = "1"
        else:
            result[column] = 0.1 + index * 0.001
    result["signal_breakout"] = (np.arange(len(result)) % 3 == 0).astype(int)
    result["signal_mean_reversion"] = (np.arange(len(result)) % 5 == 0).astype(int)
    return result


def test_build_dataset_uses_costs_targets_and_report(monkeypatch, config, history_frame):
    config.training_window_days = 365
    config.minimum_history_rows = 1
    monkeypatch.setattr(module, "calculate_features", _fake_features)
    dataset = build_dataset(config=config, raw_df=history_frame, save=False)
    assert not dataset.empty
    assert set(dataset["strategy_name"]) == {"breakout", "mean_reversion"}
    assert dataset.duplicated(["timestamp", "symbol", "strategy_name"]).sum() == 0
    assert "dataset_report" in dataset.attrs
    assert dataset.attrs["dataset_report"]["fee"] == config.fee
    expected_cost = 2 * (config.fee + config.slippage)
    row = dataset.iloc[0]
    assert np.isclose(
        row["net_return"],
        row["exit_price"] / row["entry_price"] - 1 - expected_cost,
    )


def test_build_dataset_save_writes_dataset_and_report(monkeypatch, config, history_frame):
    config.training_window_days = 365
    monkeypatch.setattr(module, "calculate_features", _fake_features)
    writes = {}
    monkeypatch.setattr(module, "_atomic_write_parquet", lambda df, path: writes.setdefault("dataset", (df.copy(), path)))
    monkeypatch.setattr(module, "_atomic_write_json", lambda payload, path: writes.setdefault("report", (payload, path)))
    dataset = build_dataset(config=config, raw_df=history_frame, save=True)
    assert len(writes["dataset"][0]) == len(dataset)
    assert writes["dataset"][1] == config.dataset_path
    assert writes["report"][1].name == "latest_dataset_report.json"


def test_build_dataset_rejects_empty_history(config):
    try:
        build_dataset(config=config, raw_df=pd.DataFrame(), save=False)
    except ValueError as error:
        assert "history is empty" in str(error)
    else:
        raise AssertionError("empty history must be rejected")

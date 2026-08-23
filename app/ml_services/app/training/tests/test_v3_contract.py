from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.features_builder import CAT_FEATURES, FEATURE_COLUMNS, build_inference_features
from app.online.model_predictor import ModelPredictor
from app.training.model_registry import ModelRegistry
from app.training.target_config import horizon_bars
from app.training.time_split import global_time_split


def _candles(count: int = 120) -> list[dict]:
    result = []
    for index, timestamp in enumerate(pd.date_range("2026-01-01", periods=count, freq="h")):
        close = 100 + index * 0.05 + np.sin(index / 5)
        result.append(
            {
                "timestamp": timestamp,
                "open": close - 0.1,
                "high": close + 0.4,
                "low": close - 0.4,
                "close": close,
                "volume": 1000 + index * 3,
            }
        )
    return result


def test_interval_is_part_of_train_and_inference_schema():
    assert "interval" in FEATURE_COLUMNS
    assert "interval" in CAT_FEATURES
    features = build_inference_features(
        _candles(),
        symbol="BTCUSDT",
        strategy_name="breakout",
        interval="1h",
    )
    assert features.iloc[0]["interval"] == "1h"
    assert set(FEATURE_COLUMNS).issubset(features.columns)
    assert {"hour", "weekday"}.issubset(features.columns)


def test_fixed_time_horizon_conversion():
    assert horizon_bars(180, "1m") == 180
    assert horizon_bars(180, "5m") == 36
    assert horizon_bars(180, "15m") == 12
    assert horizon_bars(180, "1h") == 3
    with pytest.raises(ValueError):
        horizon_bars(180, "4h")


def test_physical_purge_gap(model_frame):
    split = global_time_split(
        model_frame,
        0.70,
        0.15,
        0.15,
        purge_timedelta=pd.Timedelta(hours=4),
    )
    assert split.train["timestamp"].max() < split.validation["timestamp"].min() - pd.Timedelta(hours=4)
    assert split.validation["timestamp"].max() < split.test["timestamp"].min() - pd.Timedelta(hours=4)


def test_negative_candidate_cannot_be_promoted(config):
    registry = ModelRegistry(config)
    metrics = {
        "classification": {
            "single_class_test": False,
            "roc_auc": 0.60,
            "pr_auc": 0.40,
            "positive_class_rate": 0.25,
            "brier_score": 0.18,
        },
        "probabilities": {
            "unique_count": 200,
            "std": 0.10,
            "range": 0.50,
        },
        "trading": {
            "trades": 100,
            "mean_net_return": -0.001,
            "total_net_return": -0.10,
            "maximum_drawdown": -0.10,
            "profit_factor": 0.8,
            "by_symbol": {"BTCUSDT": {"trades": 50}, "ETHUSDT": {"trades": 50}},
            "by_strategy": {"breakout": {"trades": 50}, "mean_reversion": {"trades": 50}},
        },
    }
    report = {
        "walk_forward": {"completed_folds": 4, "positive_return_fold_rate": 0.75},
        "sensitivity": {"warnings": []},
    }
    passed, reasons = registry.promotion_gate(metrics, None, report)
    assert not passed
    assert "total net return is not positive" in reasons
    assert "profit factor is not above minimum" in reasons


def test_promote_requires_validation_artifact(config):
    registry = ModelRegistry(config)
    candidate = registry.create_candidate_dir("v3")
    (candidate / "model.cbm").write_bytes(b"model")
    (candidate / "config.json").write_text(json.dumps({"model_version": "v3"}))
    (candidate / "metrics.json").write_text("{}")
    with pytest.raises(RuntimeError, match="promotion decision"):
        registry.promote("v3")

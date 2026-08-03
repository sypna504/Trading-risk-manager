from __future__ import annotations

import numpy as np
import pandas as pd

from app.training import evaluate_model as module
from app.training.evaluate_model import (
    _group_stability,
    _max_drawdown_from_returns,
    _safe_float,
    calibration_curve_points,
    compute_permutation_importance,
    evaluate_predictions,
    expected_calibration_error,
    trading_metrics,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=6, freq="h"),
            "symbol": ["BTCUSDT", "ETHUSDT"] * 3,
            "strategy_name": ["breakout", "mean_reversion"] * 3,
            "target_good_trade": [0, 1, 0, 1, 0, 1],
            "net_return": [-0.01, 0.02, -0.005, 0.015, -0.004, 0.01],
            "max_drawdown": [-0.02, -0.005, -0.01, -0.004, -0.01, -0.003],
        }
    )


def test_safe_float():
    assert _safe_float("1.5") == 1.5
    assert _safe_float("bad") is None
    assert _safe_float(np.inf) is None


def test_calibration_metrics():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    assert expected_calibration_error(y, p, bins=2) < 0.2
    points = calibration_curve_points(y, p, bins=2)
    assert sum(point["count"] for point in points) == 4


def test_drawdown_and_group_stability():
    returns = pd.Series([0.1, -0.2, 0.05])
    assert _max_drawdown_from_returns(returns) < 0
    assert np.isnan(_max_drawdown_from_returns(pd.Series(dtype=float)))
    grouped = _group_stability(_frame(), "symbol")
    assert set(grouped) == {"BTCUSDT", "ETHUSDT"}
    assert _group_stability(_frame().iloc[:0], "symbol") == {}


def test_trading_metrics_empty_and_selected():
    frame = _frame()
    probabilities = np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.7])
    selected = trading_metrics(frame, probabilities, 0.5)
    assert selected["trades"] == 3
    assert selected["mean_net_return"] > 0
    assert selected["by_symbol"]
    empty = trading_metrics(frame, probabilities, 0.99)
    assert empty["trades"] == 0
    assert empty["maximum_drawdown"] is None


def test_evaluate_predictions_two_classes_and_single_class():
    frame = _frame()
    probabilities = np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.7])
    result = evaluate_predictions(frame, probabilities, 0.5)
    assert result["classification"]["roc_auc"] == 1.0
    assert result["classification"]["single_class_test"] is False
    assert result["probabilities"]["unique_count"] == 6

    single = frame.iloc[[1, 3, 5]].copy()
    single_result = evaluate_predictions(single, np.array([0.7, 0.8, 0.9]), 0.5)
    assert single_result["classification"]["single_class_test"] is True
    assert single_result["classification"]["roc_auc"] is None


def test_evaluate_predictions_model_metadata():
    class FakeModel:
        tree_count_ = 7

        def get_best_iteration(self):
            return 4

        def get_feature_importance(self):
            return [2.0, 1.0]

    result = evaluate_predictions(
        _frame(),
        np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.7]),
        0.5,
        model=FakeModel(),
        feature_names=["a", "b"],
    )
    assert result["model"]["tree_count"] == 7
    assert list(result["model"]["feature_importance"])[0] == "a"


def test_compute_permutation_importance_success_and_failure(monkeypatch):
    class Result:
        importances_mean = np.array([0.2, 0.1])

    monkeypatch.setattr(module, "permutation_importance", lambda *args, **kwargs: Result())
    x = pd.DataFrame({"a": range(10), "b": range(10)})
    y = pd.Series([0, 1] * 5)
    result = compute_permutation_importance(object(), x, y, ["a", "b"], 42, max_rows=5)
    assert result == {"a": 0.2, "b": 0.1}

    def fail(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(module, "permutation_importance", fail)
    assert compute_permutation_importance(object(), x, y, ["a", "b"], 42) == {}

from __future__ import annotations

import numpy as np
import pandas as pd

from app.training import window_selection as module
from app.training.window_selection import _exclude_final_holdout, compare_training_windows


def test_exclude_final_holdout(model_frame):
    result = _exclude_final_holdout(model_frame, 0.2)
    assert result["timestamp"].max() < model_frame["timestamp"].max()
    assert len(result) < len(model_frame)


def test_compare_training_windows_selects_best(monkeypatch, config, model_frame):
    config.training_window_candidates = [90, 180]
    config.walk_forward_folds = 1

    def fake_build(local_config, raw_df=None, save=False):
        result = model_frame.copy()
        result.attrs["days"] = local_config.training_window_days
        return result

    monkeypatch.setattr(module, "build_dataset", fake_build)
    monkeypatch.setattr(
        module,
        "walk_forward_time_splits",
        lambda data, **kwargs: [
            (data.iloc[:80], data.iloc[80:120], data.iloc[120:160])
        ],
    )

    class FakeModel:
        def predict_proba(self, pool):
            count = pool.num_row()
            p = np.linspace(0.2, 0.8, count)
            return np.column_stack([1 - p, p])

    monkeypatch.setattr(module, "_fit_catboost", lambda *args, **kwargs: FakeModel())
    monkeypatch.setattr(module, "select_threshold", lambda *args, **kwargs: (0.5, []))

    def fake_evaluate(test, probabilities, threshold):
        days = 180 if len(test) else 90
        return {"trading": {"total_net_return": 1.0}, "classification": {}}

    monkeypatch.setattr(module, "evaluate_predictions", fake_evaluate)
    result = compare_training_windows(model_frame, config)
    assert result["selected_training_window_days"] in {90, 180}
    assert result["selection_reason"] == "best pre-test walk-forward stability"


def test_compare_training_windows_falls_back_on_errors(monkeypatch, config, model_frame):
    config.training_window_candidates = [90]
    monkeypatch.setattr(module, "build_dataset", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad")))
    result = compare_training_windows(model_frame, config)
    assert result["selected_training_window_days"] == config.training_window_days
    assert result["windows"][0]["error"] == "bad"

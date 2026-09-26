from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from catboost import Pool
from sklearn.isotonic import IsotonicRegression

from app.features_builder import CAT_FEATURES, FEATURE_COLUMNS
from app.training import train_model as module
from app.training.model_registry import ModelRegistry
from app.training.time_split import TimeSplit
from app.training.train_model import (
    _baseline_reports,
    _catboost_frame,
    _choose_calibration,
    _fit_calibrator,
    _fit_catboost,
    _fit_logistic_baseline,
    _model_score,
    _pool,
    _threshold_candidates,
    _validation_parts,
    _walk_forward_report,
    apply_calibrator,
    evaluate_bundle_on_test,
    load_model_bundle,
    select_threshold,
    train_candidate,
    train_model,
)
from app.training.training_config import TrainingConfig


SMALL_PARAMS = {
    "name": "small",
    "iterations": 8,
    "learning_rate": 0.1,
    "depth": 2,
    "l2_leaf_reg": 3.0,
    "random_strength": 0.1,
    "bagging_temperature": 0.1,
    "border_count": 16,
}


def test_catboost_frame_and_pool(model_frame):
    frame = _catboost_frame(model_frame.head(10))
    assert list(frame.columns) == FEATURE_COLUMNS
    assert all(frame[column].dtype == object for column in CAT_FEATURES)
    labelled = _pool(model_frame.head(10))
    unlabelled = _pool(model_frame.head(10), with_label=False)
    assert isinstance(labelled, Pool)
    assert labelled.num_row() == 10
    assert unlabelled.num_row() == 10


def test_validation_parts_success_and_error(model_frame):
    evaluation, calibration, threshold = _validation_parts(model_frame, purge_bars=2)
    assert not evaluation.empty
    assert not threshold.empty
    assert set(evaluation["timestamp"]).isdisjoint(set(threshold["timestamp"]))
    with pytest.raises(ValueError, match="at least 12"):
        _validation_parts(model_frame[model_frame["timestamp"].isin(model_frame["timestamp"].unique()[:5])], 1)


def test_fit_catboost_and_model_score(config, model_frame):
    train = model_frame.iloc[:160].copy()
    evaluation = model_frame.iloc[160:220].copy()
    model = _fit_catboost(train, evaluation, SMALL_PARAMS, config)
    score = _model_score(model, evaluation)
    assert np.isfinite(score)


def test_fit_and_apply_calibrators():
    probabilities = np.array([0.1, 0.2, 0.8, 0.9])
    y = np.array([0, 0, 1, 1])
    isotonic = _fit_calibrator(probabilities, y, "isotonic")
    platt = _fit_calibrator(probabilities, y, "platt")
    assert isinstance(isotonic, IsotonicRegression)
    assert apply_calibrator(None, probabilities).tolist() == probabilities.tolist()
    assert len(apply_calibrator(isotonic, probabilities)) == 4
    assert len(apply_calibrator(platt, probabilities)) == 4


def test_choose_calibration_disabled_and_enabled(monkeypatch, config, model_frame):
    class FakeModel:
        def predict_proba(self, pool):
            count = pool.num_row()
            values = np.linspace(0.05, 0.95, count)
            return np.column_stack([1 - values, values])

    calibration = model_frame.iloc[:40].copy()
    threshold = model_frame.iloc[40:80].copy()
    config.enable_calibration = False
    calibrator, probabilities, report = _choose_calibration(
        FakeModel(), calibration, threshold, config
    )
    assert calibrator is None
    assert report["enabled"] is False
    assert len(probabilities) == len(threshold)

    config.enable_calibration = True
    monkeypatch.setattr(module, "brier_score_loss", lambda y, p: 0.2 if np.allclose(p, np.linspace(0.05, 0.95, len(p))) else 0.1)
    calibrator, probabilities, report = _choose_calibration(
        FakeModel(), calibration, threshold, config
    )
    assert report["method"] in {None, config.calibration_method}
    assert len(probabilities) == len(threshold)


def test_threshold_candidates_and_selection(config, model_frame):
    config.threshold_min = 0.4
    config.threshold_max = 0.6
    config.threshold_step = 0.1
    config.minimum_selected_trades = 2
    probabilities = np.linspace(0.1, 0.9, len(model_frame))
    candidates = _threshold_candidates(config)
    assert np.allclose(candidates, [0.4, 0.5, 0.6])
    threshold, table = select_threshold(model_frame, probabilities, config)
    assert threshold in candidates
    assert len(table) == 3


def test_logistic_and_baseline_reports(model_frame):
    train = model_frame.iloc[:160].copy()
    test = model_frame.iloc[160:].copy()
    model = _fit_logistic_baseline(train)
    assert model.predict_proba(_catboost_frame(test)).shape[1] == 2
    reports = _baseline_reports(train, test, 0.5)
    assert "constant" in reports
    assert "logistic_regression" in reports


def test_walk_forward_report_handles_empty_folds(monkeypatch, config, model_frame):
    monkeypatch.setattr(module, "walk_forward_time_splits", lambda *args, **kwargs: [])
    result = _walk_forward_report(model_frame, SMALL_PARAMS, 0.5, config)
    assert result["completed_folds"] == 0
    assert result["positive_return_fold_rate"] is None


def test_train_candidate_and_bundle_evaluation(monkeypatch, config, model_frame):
    config.walk_forward_folds = 0
    config.enable_calibration = False
    config.minimum_selected_trades = 1
    config.minimum_selected_rate = 0.0
    config.maximum_selected_rate = 1.0
    monkeypatch.setattr(
        TrainingConfig,
        "model_search_space",
        property(lambda self: [SMALL_PARAMS]),
    )
    monkeypatch.setattr(module, "compute_permutation_importance", lambda *args, **kwargs: {})
    registry = ModelRegistry(config)
    result = train_candidate(model_frame, config=config, registry=registry)
    assert result["candidate_dir"].exists()
    assert (result["candidate_dir"] / "model.cbm").exists()
    assert (result["candidate_dir"] / "config.json").exists()
    assert result["metrics"]["classification"]

    model, payload, calibrator = load_model_bundle(result["candidate_dir"])
    assert payload["model_version"] == result["version"]
    assert calibrator is None
    evaluation = evaluate_bundle_on_test(result["candidate_dir"], result["test_frame"])
    assert "classification" in evaluation


def test_train_model_entrypoint(monkeypatch, config, model_frame, capsys):
    monkeypatch.setattr(TrainingConfig, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(pd, "read_parquet", lambda path: model_frame)
    monkeypatch.setattr(
        module,
        "train_candidate",
        lambda dataset, config=None: {
            "candidate_dir": Path("candidate"),
            "version": "v1",
        },
    )
    train_model()
    output = capsys.readouterr().out
    assert "candidate saved" in output
    assert "v1" in output

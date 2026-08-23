from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from catboost import CatBoostClassifier, Pool
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from app.online.model_predictor import ModelPredictor, _apply_calibrator, _checksum
from app.training.model_registry import atomic_write_json


def _write_bundle(root: Path, version: str, threshold: float = 0.5) -> Path:
    bundle = root / "active" / version
    bundle.mkdir(parents=True)
    x = pd.DataFrame(
        {
            "x": [0.0, 1.0, 0.1, 0.9, 0.2, 0.8],
            "symbol": ["BTCUSDT"] * 6,
        }
    )
    y = [0, 1, 0, 1, 0, 1]
    model = CatBoostClassifier(
        iterations=5,
        depth=2,
        verbose=False,
        allow_writing_files=False,
        random_seed=42,
    )
    model.fit(Pool(x, label=y, cat_features=["symbol"]))
    model_path = bundle / "model.cbm"
    model.save_model(str(model_path))
    config = {
        "model_version": version,
        "threshold": threshold,
        "feature_cols": ["x", "symbol"],
        "cat_features": ["symbol"],
        "train_start": "2026-01-01",
        "train_end": "2026-01-02",
        "calibrator": None,
        "model_checksum": _checksum(model_path),
    }
    (bundle / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return bundle


def _registry(version: str) -> dict:
    return {
        "active_model_version": version,
        "previous_model_version": None,
        "active_model_path": f"active/{version}/model.cbm",
        "active_config_path": f"active/{version}/config.json",
        "promoted_at": "2026-08-02T00:00:00Z",
        "rollback_available": False,
        "candidate_history": [],
    }


def test_checksum(tmp_path):
    path = tmp_path / "file"
    path.write_bytes(b"abc")
    assert len(_checksum(path)) == 64


def test_apply_calibrator_none_isotonic_and_logistic():
    assert _apply_calibrator(None, 0.4) == 0.4
    iso = IsotonicRegression(out_of_bounds="clip").fit([0.1, 0.9], [0, 1])
    assert 0 <= _apply_calibrator(iso, 0.5) <= 1
    logistic = LogisticRegression().fit(np.array([[0.1], [0.2], [0.8], [0.9]]), [0, 0, 1, 1])
    assert 0 <= _apply_calibrator(logistic, 0.5) <= 1


def test_predictor_legacy_load_predict_metadata_and_no_reload(tmp_path):
    models_root = tmp_path / "models"
    bundle = _write_bundle(models_root, "v1")
    predictor = ModelPredictor(
        model_path=bundle / "model.cbm",
        config_path=bundle / "config.json",
        models_root=models_root,
    )
    assert predictor.reload(force=False) is False
    result = predictor.predict(pd.DataFrame({"x": [0.9], "symbol": ["BTCUSDT"]}))
    assert result["model_version"] == "v1"
    assert 0 <= result["prob_good_trade"] <= 1
    metadata = predictor.metadata()
    assert metadata["model_version"] == "v1"
    assert metadata["loaded_at"] is not None


def test_predictor_registry_resolve_and_hot_reload(tmp_path):
    models_root = tmp_path / "models"
    _write_bundle(models_root, "v1")
    _write_bundle(models_root, "v2")
    registry_path = models_root / "registry.json"
    atomic_write_json(_registry("v1"), registry_path)
    predictor = ModelPredictor(
        model_path=models_root / "legacy.cbm",
        config_path=models_root / "legacy.json",
        registry_path=registry_path,
        models_root=models_root,
    )
    model_path, config_path, mtime = predictor._resolve_paths()
    assert model_path.name == "model.cbm"
    assert config_path.name == "config.json"
    assert mtime is not None
    assert predictor.predict(pd.DataFrame({"x": [0.9], "symbol": ["BTCUSDT"]}))["model_version"] == "v1"
    atomic_write_json(_registry("v2"), registry_path)
    assert predictor.predict(pd.DataFrame({"x": [0.9], "symbol": ["BTCUSDT"]}))["model_version"] == "v2"


def test_predictor_validation_errors(tmp_path):
    models_root = tmp_path / "models"
    bundle = _write_bundle(models_root, "v1")
    predictor = ModelPredictor(bundle / "model.cbm", bundle / "config.json")
    with pytest.raises(ValueError, match="missing model features"):
        predictor.predict(pd.DataFrame({"x": [0.9]}))
    with pytest.raises(ValueError, match="inf"):
        predictor.predict(pd.DataFrame({"x": [np.inf], "symbol": ["BTCUSDT"]}))


def test_predictor_missing_initial_files_and_rejects_bad_reload(tmp_path, capsys):
    with pytest.raises(FileNotFoundError, match="model not found"):
        ModelPredictor(tmp_path / "missing.cbm", tmp_path / "missing.json")

    models_root = tmp_path / "models"
    _write_bundle(models_root, "v1")
    _write_bundle(models_root, "v2")
    registry_path = models_root / "registry.json"
    atomic_write_json(_registry("v1"), registry_path)
    predictor = ModelPredictor(
        models_root / "missing.cbm",
        models_root / "missing.json",
        registry_path,
        models_root,
    )
    v2_config = models_root / "active" / "v2" / "config.json"
    payload = json.loads(v2_config.read_text())
    payload["model_checksum"] = "bad"
    v2_config.write_text(json.dumps(payload), encoding="utf-8")
    atomic_write_json(_registry("v2"), registry_path)
    predictor.maybe_reload()
    assert predictor.model_version == "v1"
    assert "keeping current model" in capsys.readouterr().out

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from catboost import CatBoostClassifier, Pool

from app.online.model_predictor import ModelPredictor
from app.training.model_registry import atomic_write_json


def _write_bundle(root: Path, version: str) -> None:
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
    model.save_model(str(bundle / "model.cbm"))
    (bundle / "config.json").write_text(
        json.dumps(
            {
                "model_version": version,
                "threshold": 0.5,
                "feature_cols": ["x", "symbol"],
                "cat_features": ["symbol"],
                "train_start": "2026-01-01",
                "train_end": "2026-01-02",
                "calibrator": None,
            }
        ),
        encoding="utf-8",
    )


def _registry_payload(version: str) -> dict:
    return {
        "active_model_version": version,
        "previous_model_version": None,
        "active_model_path": f"active/{version}/model.cbm",
        "active_config_path": f"active/{version}/config.json",
        "promoted_at": "2026-08-02T00:00:00Z",
        "rollback_available": False,
        "candidate_history": [],
    }


def test_predictor_hot_reloads_promoted_model(tmp_path):
    models_root = tmp_path / "models"
    _write_bundle(models_root, "v1")
    _write_bundle(models_root, "v2")
    registry_path = models_root / "registry.json"
    atomic_write_json(_registry_payload("v1"), registry_path)

    predictor = ModelPredictor(
        model_path=models_root / "missing_legacy.cbm",
        config_path=models_root / "missing_legacy.json",
        registry_path=registry_path,
        models_root=models_root,
    )
    features = pd.DataFrame({"x": [0.9], "symbol": ["BTCUSDT"]})
    assert predictor.predict(features)["model_version"] == "v1"

    atomic_write_json(_registry_payload("v2"), registry_path)
    assert predictor.predict(features)["model_version"] == "v2"

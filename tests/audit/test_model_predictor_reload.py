import json

import pandas as pd
import pytest

from app.ml_services.app.online import model_predictor as module


class FakeModel:
    load_count = 0

    def load_model(self, _path):
        type(self).load_count += 1

    def predict_proba(self, _pool):
        return [[0.2, 0.8]]


def _build_predictor(tmp_path, monkeypatch):
    model_path = tmp_path / "model.cbm"
    config_path = tmp_path / "config.json"
    model_path.write_bytes(b"model")
    config_path.write_text(
        json.dumps(
            {
                "model_version": "v1",
                "threshold": 0.5,
                "feature_cols": ["x"],
                "cat_features": [],
            }
        ),
        encoding="utf-8",
    )
    FakeModel.load_count = 0
    monkeypatch.setattr(module, "CatBoostClassifier", FakeModel)
    monkeypatch.setattr(module, "Pool", lambda **kwargs: kwargs)
    return module.ModelPredictor(model_path, config_path)


def test_legacy_predictor_does_not_reload_on_every_request(tmp_path, monkeypatch):
    predictor = _build_predictor(tmp_path, monkeypatch)
    assert FakeModel.load_count == 1
    predictor.maybe_reload()
    predictor.maybe_reload()
    assert FakeModel.load_count == 1


def test_predictor_rejects_nan_features(tmp_path, monkeypatch):
    predictor = _build_predictor(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="NaN or inf"):
        predictor.predict(pd.DataFrame({"x": [float("nan")]}))

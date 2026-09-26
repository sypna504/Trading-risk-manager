import json
from pathlib import Path

import pytest

from app.backend.api.app.config import settings
from app.backend.api.app.services.model_metadata_service import (
    read_active_model_metadata,
)


def test_model_metadata_uses_active_registry_bundle(tmp_path, monkeypatch):
    bundle = tmp_path / "active" / "risk_model_test"
    bundle.mkdir(parents=True)
    (bundle / "model.cbm").write_bytes(b"model")
    (bundle / "config.json").write_text(
        json.dumps(
            {
                "model_version": "risk_model_test",
                "threshold": 0.6,
                "feature_cols": ["x"],
                "cat_features": [],
            }
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "active_model_version": "risk_model_test",
                "active_model_path": "active/risk_model_test/model.cbm",
                "active_config_path": "active/risk_model_test/config.json",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "MODELS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "MODEL_REGISTRY_PATH", str(registry))

    metadata = read_active_model_metadata()
    assert metadata["model_version"] == "risk_model_test"
    assert metadata["model_file_exists"] is True
    assert metadata["config"]["threshold"] == 0.6


def test_model_metadata_rejects_registry_path_traversal(tmp_path, monkeypatch):
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "active_model_version": "bad",
                "active_model_path": "../outside.cbm",
                "active_config_path": "../outside.json",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "MODELS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "MODEL_REGISTRY_PATH", str(registry))
    with pytest.raises(ValueError, match="unsafe"):
        read_active_model_metadata()

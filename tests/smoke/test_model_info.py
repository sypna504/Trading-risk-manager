import json
from pathlib import Path

from app.backend.api.app.config import settings
from app.backend.api.app.routers.ml_service_router import get_model_info


def test_model_info_reads_config(monkeypatch, tmp_path: Path):
    model_path = tmp_path / "model.cbm"
    config_path = tmp_path / "config.json"
    model_path.write_bytes(b"model")
    config_path.write_text(
        json.dumps(
            {
                "model_version": "risk_model_0208",
                "threshold": 0.5,
                "train_start": "2026-01-01 00:00:00",
                "train_end": "2026-08-01 00:00:00",
                "feature_cols": ["ret_1", "rsi_14"],
                "cat_features": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "MODEL_PATH", str(model_path))
    monkeypatch.setattr(settings, "MODEL_CONFIG_PATH", str(config_path))

    result = get_model_info()

    assert result.model_version == "risk_model_0208"
    assert result.feature_count == 2
    assert result.model_file_exists is True

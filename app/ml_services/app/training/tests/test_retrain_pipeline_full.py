from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from app.training import retrain_pipeline as module
from app.training.data_validation import ValidationResult
from app.training.retrain_pipeline import (
    FEATURE_COLUMNS_IMPORT,
    _dataset_hash,
    _hours_since,
    _print_status,
    _read_last_run,
    _restart_service,
    _utc_now,
    _verify_inference_version,
    _write_run_report,
    main,
    run_pipeline,
)
from app.training.training_config import TrainingConfig


def test_time_hash_and_last_run(config):
    assert _utc_now().tzinfo is not None
    assert _dataset_hash(config.dataset_path) is None
    config.dataset_path.parent.mkdir(parents=True, exist_ok=True)
    config.dataset_path.write_bytes(b"abc")
    assert len(_dataset_hash(config.dataset_path)) == 64
    assert _read_last_run(config) == {}
    config.reports_path.mkdir(parents=True, exist_ok=True)
    (config.reports_path / "last_run_state.json").write_text(
        json.dumps({"value": 1}), encoding="utf-8"
    )
    assert _read_last_run(config) == {"value": 1}
    assert _hours_since(None) is None
    assert _hours_since(pd.Timestamp.now(tz="UTC").isoformat()) < 0.1


def test_restart_service(monkeypatch, config):
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda command, check: calls.append((command, check)))
    _restart_service(config)
    assert calls[0][0][-1] == config.docker_compose_service
    assert calls[0][1] is True


def test_verify_inference_version(monkeypatch):
    assert _verify_inference_version("", "v1")["skipped"] is True

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"model_version": "v1"}).encode()

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert _verify_inference_version("http://internal", "v1")["model_version"] == "v1"
    with pytest.raises(RuntimeError, match="version mismatch"):
        _verify_inference_version("http://internal", "v2")


def test_write_run_report_and_feature_import(config):
    path = _write_run_report(config, "run_test", {"status": "ok"})
    assert json.loads(path.read_text())["status"] == "ok"
    assert (config.reports_path / "latest_training_report.json").exists()
    assert FEATURE_COLUMNS_IMPORT()


def test_run_pipeline_skip(monkeypatch, config):
    config.retrain_on_data_change_only = True
    config.minimum_new_candles = 1
    monkeypatch.setattr(module, "_read_last_run", lambda cfg: {"last_history_hash": "same"})
    monkeypatch.setattr(
        module,
        "update_history",
        lambda cfg: {
            "added_unique_rows": 0,
            "updated_existing_rows": 0,
            "changed_rows": 0,
            "final_rows": 10,
            "history_hash": "same",
            "validation": {"max_timestamp": "2026-01-01T00:00:00Z"},
        },
    )
    result = run_pipeline(config=config)
    assert result["status"] == "skipped"
    assert result["skip_reasons"]


def test_run_pipeline_success(monkeypatch, config, model_frame):
    config.force_retrain = True
    config.deploy_after_training = True
    config.auto_select_training_window = False
    config.inference_version_url = ""

    monkeypatch.setattr(module, "_read_last_run", lambda cfg: {})
    monkeypatch.setattr(
        module,
        "update_history",
        lambda cfg: {
            "added_unique_rows": 10,
            "updated_existing_rows": 0,
            "changed_rows": 10,
            "final_rows": 100,
            "history_hash": "new",
            "validation": {"max_timestamp": "2026-01-05T00:00:00Z"},
        },
    )
    dataset = model_frame.copy()
    dataset.attrs["dataset_report"] = {"rows": len(dataset)}
    monkeypatch.setattr(module, "build_dataset", lambda config=None: dataset)
    monkeypatch.setattr(
        module,
        "validate_dataset",
        lambda *args, **kwargs: ValidationResult(True, {"errors": []}),
    )

    class FakeRegistry:
        def __init__(self, cfg):
            self.cfg = cfg

        def bootstrap_legacy(self):
            return None

        def active_bundle_dir(self):
            return None

        def promotion_gate(self, candidate, champion):
            return True, []

        def promote(self, version):
            return {"active_model_version": version}

        def read(self):
            return {"active_model_version": "v1"}

        def update_candidate_decision(self, *args):
            raise AssertionError("should not reject")

    monkeypatch.setattr(module, "ModelRegistry", FakeRegistry)
    monkeypatch.setattr(
        module,
        "train_candidate",
        lambda dataset, config, registry: {
            "version": "v1",
            "candidate_dir": config.models_root / "candidates" / "v1",
            "metrics": {"classification": {}, "trading": {}},
            "training_report": {},
            "test_frame": dataset.iloc[-20:],
            "config": {"train_end": "2026-01-01T00:00:00Z"},
        },
    )
    monkeypatch.setattr(module, "build_drift_report", lambda *args, **kwargs: {"ok": True})
    result = run_pipeline(config=config)
    assert result["status"] == "completed"
    assert result["active_model_after_run"] == "v1"


def test_run_pipeline_failure_writes_report(monkeypatch, config):
    config.force_retrain = True
    monkeypatch.setattr(module, "update_history", lambda cfg: (_ for _ in ()).throw(ValueError("boom")))
    with pytest.raises(ValueError, match="boom"):
        run_pipeline(config=config)
    latest = json.loads((config.reports_path / "latest_training_report.json").read_text())
    assert latest["status"] == "failed"


def test_print_status_and_main_status(monkeypatch, config, capsys):
    _print_status(config)
    assert "latest_report" in capsys.readouterr().out
    monkeypatch.setattr(TrainingConfig, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(sys, "argv", ["retrain_pipeline", "--status"])
    assert main() == 0

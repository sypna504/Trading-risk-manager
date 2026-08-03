from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.training.model_registry import (
    ModelRegistry,
    atomic_write_json,
    file_checksum,
    model_version_now,
    normalize_registry_path_value,
    registry_relative_path,
    repair_registry_payload_paths,
    utc_now_iso,
)


def _good_metrics() -> dict:
    return {
        "classification": {
            "single_class_test": False,
            "roc_auc": 0.65,
            "pr_auc": 0.55,
            "positive_class_rate": 0.30,
            "brier_score": 0.18,
        },
        "probabilities": {"unique_count": 100, "std": 0.10},
        "trading": {
            "trades": 100,
            "mean_net_return": 0.002,
            "total_net_return": 0.20,
            "maximum_drawdown": -0.10,
            "by_symbol": {
                "BTCUSDT": {"trades": 50},
                "ETHUSDT": {"trades": 50},
            },
            "by_strategy": {
                "breakout": {"trades": 50},
                "mean_reversion": {"trades": 50},
            },
        },
    }


def _candidate(registry: ModelRegistry, version: str, metrics=None) -> Path:
    path = registry.create_candidate_dir(version)
    (path / "model.cbm").write_bytes(b"model")
    (path / "config.json").write_text(json.dumps({"model_version": version}), encoding="utf-8")
    (path / "metrics.json").write_text(json.dumps(metrics or _good_metrics()), encoding="utf-8")
    return path


def test_time_version_checksum_and_atomic_json(tmp_path):
    assert "+00:00" in utc_now_iso()
    assert re.fullmatch(r"risk_model_\d{8}_\d{6}", model_version_now())
    file_path = tmp_path / "file.bin"
    file_path.write_bytes(b"abc")
    assert len(file_checksum(file_path)) == 64
    json_path = tmp_path / "registry.json"
    atomic_write_json({"a": 1}, json_path)
    assert json.loads(json_path.read_text()) == {"a": 1}


def test_registry_init_empty_read_and_active_bundle(config):
    registry = ModelRegistry(config)
    assert registry.read() == registry.empty_registry()
    assert registry.active_bundle_dir() is None
    assert registry.root.exists()


def test_bootstrap_legacy(config):
    legacy_model = config.models_root / "risk_model_v2_online.cbm"
    legacy_config = config.models_root / "risk_model_v2_online_config.json"
    legacy_model.write_bytes(b"legacy")
    legacy_config.write_text(
        json.dumps(
            {
                "model_version": "legacy_v1",
                "feature_cols": ["x"],
                "cat_features": [],
                "threshold": 0.5,
            }
        ),
        encoding="utf-8",
    )
    registry = ModelRegistry(config)
    result = registry.bootstrap_legacy()
    assert result["active_model_version"] == "legacy_v1"
    assert registry.active_bundle_dir().name == "legacy_v1"
    assert registry.bootstrap_legacy()["active_model_version"] == "legacy_v1"


def test_candidate_registration_and_decision(config):
    registry = ModelRegistry(config)
    candidate = _candidate(registry, "v1")
    registry.register_candidate("v1", candidate, _good_metrics())
    item = registry.read()["candidate_history"][-1]
    assert item["version"] == "v1"
    assert item["decision"] == "trained"
    registry.update_candidate_decision("v1", "rejected", ["bad"])
    item = registry.read()["candidate_history"][-1]
    assert item["decision"] == "rejected"
    registry.update_candidate_decision("missing", "rejected", ["missing"])
    assert registry.read()["candidate_history"][-1]["version"] == "missing"


def test_promotion_gate_passes_and_detects_failures(config):
    registry = ModelRegistry(config)
    passed, reasons = registry.promotion_gate(_good_metrics(), None)
    assert passed
    assert reasons == []

    bad = _good_metrics()
    bad["classification"].update(
        {"single_class_test": True, "roc_auc": 0.5, "pr_auc": 0.2}
    )
    bad["probabilities"] = {"unique_count": 1, "std": 0.0}
    bad["trading"].update(
        {
            "trades": 1,
            "mean_net_return": -0.1,
            "total_net_return": -1.0,
            "maximum_drawdown": -0.9,
            "by_symbol": {"BTCUSDT": {"trades": 1}},
            "by_strategy": {"breakout": {"trades": 1}},
        }
    )
    passed, reasons = registry.promotion_gate(bad, None)
    assert not passed
    assert len(reasons) >= 8


def test_promotion_gate_compares_champion(config):
    registry = ModelRegistry(config)
    candidate = _good_metrics()
    champion = _good_metrics()
    champion["trading"]["total_net_return"] = 1.0
    champion["trading"]["maximum_drawdown"] = -0.01
    champion["classification"]["brier_score"] = 0.10
    passed, reasons = registry.promotion_gate(candidate, champion)
    assert not passed
    assert any("champion" in reason for reason in reasons)


def test_promote_and_rollback(config):
    registry = ModelRegistry(config)
    _candidate(registry, "v1")
    registry.register_candidate("v1", registry.candidates_dir / "v1", _good_metrics())
    promoted = registry.promote("v1")
    assert promoted["active_model_version"] == "v1"

    _candidate(registry, "v2")
    registry.register_candidate("v2", registry.candidates_dir / "v2", _good_metrics())
    promoted = registry.promote("v2")
    assert promoted["active_model_version"] == "v2"
    assert promoted["rollback_available"]

    rolled_back = registry.rollback()
    assert rolled_back["active_model_version"] == "v1"


def test_promote_and_rollback_errors(config):
    registry = ModelRegistry(config)
    with pytest.raises(FileNotFoundError, match="candidate not found"):
        registry.promote("missing")
    incomplete = registry.create_candidate_dir("incomplete")
    (incomplete / "model.cbm").write_bytes(b"x")
    with pytest.raises(FileNotFoundError, match="artifact missing"):
        registry.promote("incomplete")
    with pytest.raises(RuntimeError, match="no previous model"):
        registry.rollback()



def test_registry_paths_are_posix_and_old_windows_paths_are_repaired(config):
    registry = ModelRegistry(config)
    root = registry.root
    artifact = root / "active" / "v1" / "model.cbm"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"model")

    assert registry_relative_path(artifact, root) == "active/v1/model.cbm"
    assert normalize_registry_path_value(
        r"active\v1\model.cbm"
    ) == "active/v1/model.cbm"

    payload = registry.empty_registry()
    payload.update(
        {
            "active_model_version": "v1",
            "active_model_path": r"active\v1\model.cbm",
            "active_config_path": r"active\v1\config.json",
            "candidate_history": [
                {"version": "v1", "path": r"candidates\v1"}
            ],
        }
    )
    repaired, changed = repair_registry_payload_paths(payload)

    assert changed
    assert repaired["active_model_path"] == "active/v1/model.cbm"
    assert repaired["active_config_path"] == "active/v1/config.json"
    assert repaired["candidate_history"][0]["path"] == "candidates/v1"


def test_registry_writes_only_posix_paths_after_promotion_and_rollback(config):
    registry = ModelRegistry(config)
    _candidate(registry, "v1")
    registry.register_candidate(
        "v1",
        registry.candidates_dir / "v1",
        _good_metrics(),
    )
    promoted_v1 = registry.promote("v1")

    assert "\\" not in promoted_v1["active_model_path"]
    assert "\\" not in promoted_v1["active_config_path"]
    assert promoted_v1["active_model_path"] == "active/v1/model.cbm"

    _candidate(registry, "v2")
    registry.register_candidate(
        "v2",
        registry.candidates_dir / "v2",
        _good_metrics(),
    )
    promoted_v2 = registry.promote("v2")
    rolled_back = registry.rollback()

    assert promoted_v2["active_model_path"] == "active/v2/model.cbm"
    assert rolled_back["active_model_path"] == "active/v1/model.cbm"
    assert "\\" not in rolled_back["active_config_path"]

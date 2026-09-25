from __future__ import annotations

import json
from pathlib import Path

from app.training.model_registry import ModelRegistry, file_checksum


def _metrics(total: float = 1.0) -> dict:
    return {
        "classification": {
            "single_class_test": False,
            "roc_auc": 0.55,
            "pr_auc": 0.45,
            "positive_class_rate": 0.30,
            "brier_score": 0.20,
        },
        "probabilities": {"unique_count": 100, "std": 0.1},
        "trading": {
            "trades": 100,
            "mean_net_return": 0.001,
            "total_net_return": total,
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


def _candidate(registry: ModelRegistry, version: str) -> Path:
    path = registry.create_candidate_dir(version)
    model_path = path / "model.cbm"
    model_path.write_bytes(b"model")
    (path / "config.json").write_text(
        json.dumps({
            "model_version": version,
            "feature_schema_version": "v3",
            "supported_intervals": ["1h"],
            "supported_strategies": ["breakout", "mean_reversion"],
            "supported_symbols": ["BTCUSDT", "ETHUSDT"],
            "supported_exchanges": ["binance"],
            "allow_unseen_symbols": False,
            "target_horizon_minutes": 180,
            "entry_convention": "next_bar_open",
            "model_checksum": file_checksum(model_path),
        }),
        encoding="utf-8",
    )
    (path / "metrics.json").write_text(json.dumps(_metrics()), encoding="utf-8")
    for name in ("training_report.json", "sensitivity_report.json", "dataset_report.json"):
        (path / name).write_text("{}", encoding="utf-8")
    return path


def test_failed_gate_does_not_promote(config):
    registry = ModelRegistry(config)
    bad = _metrics(total=-1.0)
    passed, reasons = registry.promotion_gate(bad, None)
    assert not passed
    assert reasons
    assert registry.read()["active_model_version"] is None


def test_promotion_and_rollback(config):
    registry = ModelRegistry(config)
    _candidate(registry, "v1")
    registry.write_promotion_decision("v1", True, [])
    registry.promote("v1")
    assert registry.read()["active_model_version"] == "v1"

    _candidate(registry, "v2")
    registry.write_promotion_decision("v2", True, [])
    registry.promote("v2")
    assert registry.read()["active_model_version"] == "v2"
    assert registry.read()["rollback_available"]

    registry.rollback()
    assert registry.read()["active_model_version"] == "v1"

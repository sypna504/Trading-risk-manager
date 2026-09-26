from __future__ import annotations

import json
import math
import os
import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import sklearn
from ml.v1 import ml_pb2

from app.config import Settings
from app.features_builder import (
    CAT_FEATURES,
    FEATURE_COLUMNS,
    FEATURE_SCHEMA_VERSION,
    MIN_CANDLES,
    build_inference_features,
    calculate_features,
    latest_complete_feature_row,
)
from app.training.training_config import TrainingConfig


def _synthetic_candles(rows: int = 320) -> list[dict[str, Any]]:
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    index = np.arange(rows, dtype=float)
    close = 100.0 + 0.025 * index + 1.8 * np.sin(index / 8.0)
    open_price = close - 0.08 * np.cos(index / 5.0)
    high = np.maximum(open_price, close) + 0.45 + 0.03 * np.sin(index / 3.0)
    low = np.minimum(open_price, close) - 0.45 - 0.03 * np.cos(index / 4.0)
    volume = 1000.0 + 2.0 * index + 80.0 * (1.0 + np.sin(index / 7.0))
    return [
        {
            "timestamp": timestamp,
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": float(v),
        }
        for timestamp, o, h, l, c, v in zip(
            timestamps, open_price, high, low, close, volume
        )
    ]


def _run_check(name: str, check: Callable[[], Any], results: dict[str, Any]) -> None:
    try:
        value = check()
        results[name] = {"ok": True, "value": value}
    except Exception as error:  # diagnostic command must report all failures
        results[name] = {
            "ok": False,
            "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        }


def _check_static_contract() -> dict[str, Any]:
    settings = Settings(_env_file=None)
    config = TrainingConfig.from_env()
    response_fields = ml_pb2.PredictSignalQualityResponse.DESCRIPTOR.fields_by_name
    required_response_fields = {
        "prob_good_trade",
        "raw_prob_good_trade",
        "risk_score",
        "trade_allowed",
        "threshold",
        "risk_level",
        "model_version",
        "calibration_method",
        "probability_bin",
        "model_supported_interval",
    }
    missing_proto = sorted(required_response_fields - set(response_fields))
    if missing_proto:
        raise AssertionError(f"protobuf response fields are missing: {missing_proto}")
    if FEATURE_SCHEMA_VERSION != "v3":
        raise AssertionError(f"FEATURE_SCHEMA_VERSION={FEATURE_SCHEMA_VERSION!r}")
    if "interval" not in FEATURE_COLUMNS or "interval" not in CAT_FEATURES:
        raise AssertionError("interval is absent from the v3 model contract")
    if "hour" in FEATURE_COLUMNS or "weekday" in FEATURE_COLUMNS:
        raise AssertionError("legacy time features are still in FEATURE_COLUMNS")
    if config.supported_intervals != ["1h"]:
        raise AssertionError(
            f"supported_intervals={config.supported_intervals!r}, expected ['1h']"
        )
    if config.target_horizon_minutes != 180:
        raise AssertionError(
            f"target_horizon_minutes={config.target_horizon_minutes}, expected 180"
        )
    if settings.MIN_CANDLES != MIN_CANDLES:
        raise AssertionError(
            f"MIN_CANDLES mismatch: settings={settings.MIN_CANDLES}, features={MIN_CANDLES}"
        )
    if sklearn.__version__ != "1.8.0":
        raise AssertionError(
            f"scikit-learn={sklearn.__version__}, expected 1.8.0 for legacy calibrator"
        )
    return {
        "sklearn": sklearn.__version__,
        "min_candles": MIN_CANDLES,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_count": len(FEATURE_COLUMNS),
        "supported_intervals": config.supported_intervals,
        "target_horizon_minutes": config.target_horizon_minutes,
        "dataset_path": str(config.dataset_path),
    }


def _check_feature_builder() -> dict[str, Any]:
    candles = _synthetic_candles()
    raw = pd.DataFrame(candles)
    raw["symbol"] = "BTCUSDT"
    raw["interval"] = "1h"
    calculated = calculate_features(raw)
    backend_contract = [
        "timestamp",
        "close",
        "atr_14_pct",
        "rsi_14",
        "price_z_20",
        "volume_z_20",
        "high_20",
        "signal_breakout",
        "signal_mean_reversion",
    ]
    backend_row = latest_complete_feature_row(calculated, backend_contract)
    features = build_inference_features(
        candles=candles,
        symbol="BTCUSDT",
        strategy_name="mean_reversion",
        interval="1h",
    )
    required_legacy = {"hour", "weekday"}
    missing_legacy = sorted(required_legacy - set(features.columns))
    if missing_legacy:
        raise AssertionError(
            f"legacy active-model compatibility columns are missing: {missing_legacy}"
        )
    if not set(FEATURE_COLUMNS).issubset(features.columns):
        missing = sorted(set(FEATURE_COLUMNS) - set(features.columns))
        raise AssertionError(f"v3 inference features are missing: {missing}")
    numeric_columns = [name for name in FEATURE_COLUMNS if name not in CAT_FEATURES]
    values = features[numeric_columns].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise AssertionError("synthetic inference features contain NaN or inf")
    return {
        "calculated_rows": len(calculated),
        "backend_row_timestamp": str(backend_row.iloc[0]["timestamp"]),
        "inference_columns": len(features.columns),
        "legacy_columns_present": sorted(required_legacy),
    }


def _check_active_model() -> dict[str, Any]:
    if os.getenv("RUNTIME_CHECK_ACTIVE_MODEL", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return {"skipped": True, "reason": "RUNTIME_CHECK_ACTIVE_MODEL is not enabled"}
    settings = Settings(_env_file=None)
    registry_path = Path(settings.MODEL_REGISTRY_PATH)
    if not registry_path.exists():
        return {"skipped": True, "reason": f"registry not found: {registry_path}"}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not registry.get("active_model_version"):
        return {"skipped": True, "reason": "registry has no active model"}

    from app.online.model_predictor import ModelPredictor

    predictor = ModelPredictor(
        model_path=settings.MODEL_PATH,
        config_path=settings.MODEL_CONFIG_PATH,
        registry_path=settings.MODEL_REGISTRY_PATH,
        models_root=settings.MODELS_ROOT,
    )
    features = build_inference_features(
        candles=_synthetic_candles(),
        symbol="BTCUSDT",
        strategy_name="mean_reversion",
        interval="1h",
    )
    prediction = predictor.predict(features)
    for name in ("raw_prob_good_trade", "prob_good_trade", "risk_score", "threshold"):
        value = float(prediction[name])
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise AssertionError(f"invalid active-model output {name}={value}")
    return {
        "skipped": False,
        "metadata": predictor.metadata(),
        "prediction": prediction,
    }


def main() -> int:
    results: dict[str, Any] = {}
    _run_check("static_contract", _check_static_contract, results)
    _run_check("feature_builder", _check_feature_builder, results)
    _run_check("active_model", _check_active_model, results)
    ok = all(item.get("ok") for item in results.values())
    payload = {"ok": ok, "checks": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

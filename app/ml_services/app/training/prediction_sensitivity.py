from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from catboost import Pool
from sklearn.isotonic import IsotonicRegression


def _apply_calibrator(calibrator: Any | None, probabilities: np.ndarray) -> np.ndarray:
    values = np.asarray(probabilities, dtype=float)
    if calibrator is None:
        return values
    if isinstance(calibrator, IsotonicRegression):
        return np.asarray(calibrator.predict(values), dtype=float)
    return np.asarray(calibrator.predict_proba(values.reshape(-1, 1))[:, 1], dtype=float)


def _predict(model, calibrator, frame: pd.DataFrame, cat_features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    prepared = frame.copy()
    for column in cat_features:
        prepared[column] = prepared[column].astype(str)
    raw = model.predict_proba(Pool(prepared, cat_features=cat_features))[:, 1]
    calibrated = _apply_calibrator(calibrator, raw)
    return np.asarray(raw, dtype=float), np.asarray(calibrated, dtype=float)


def _range(values: np.ndarray) -> float:
    return float(np.ptp(values)) if len(values) else 0.0


def build_sensitivity_report(
    model,
    calibrator,
    frame: pd.DataFrame,
    cat_features: list[str],
    supported_symbols: list[str],
    supported_strategies: list[str],
    supported_intervals: list[str],
) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("sensitivity frame is empty")
    base = frame.iloc[[0]].copy()
    warnings: list[str] = []

    def categorical_test(column: str, values: list[str]) -> dict[str, Any]:
        if column not in base.columns or not values:
            return {"values": [], "raw": [], "calibrated": [], "raw_range": 0.0, "calibrated_range": 0.0}
        rows = pd.concat([base.copy() for _ in values], ignore_index=True)
        rows[column] = values
        raw, calibrated = _predict(model, calibrator, rows, cat_features)
        return {
            "values": values,
            "raw": raw.tolist(),
            "calibrated": calibrated.tolist(),
            "raw_range": _range(raw),
            "calibrated_range": _range(calibrated),
        }

    symbol_values = supported_symbols[: min(len(supported_symbols), 8)]
    symbol = categorical_test("symbol", symbol_values)
    strategy = categorical_test("strategy_name", supported_strategies)
    interval = categorical_test("interval", supported_intervals)

    numerical_specs = {
        "rsi_14": [20.0, 50.0, 80.0],
        "atr_14_pct": [0.002, 0.01, 0.03],
        "ret_1": [-0.02, 0.0, 0.02],
        "volume_z_20": [-2.0, 0.0, 2.0],
        "ema_distance_20": [-0.03, 0.0, 0.03],
    }
    numerical: dict[str, Any] = {}
    for column, values in numerical_specs.items():
        if column not in base.columns:
            continue
        rows = pd.concat([base.copy() for _ in values], ignore_index=True)
        rows[column] = values
        raw, calibrated = _predict(model, calibrator, rows, cat_features)
        numerical[column] = {
            "values": values,
            "raw": raw.tolist(),
            "calibrated": calibrated.tolist(),
            "raw_range": _range(raw),
            "calibrated_range": _range(calibrated),
        }

    sample = frame.head(min(len(frame), 1000)).copy()
    raw_sample, calibrated_sample = _predict(model, calibrator, sample, cat_features)
    raw_std = float(np.std(raw_sample))
    calibrated_std = float(np.std(calibrated_sample))
    if raw_std <= 1e-6:
        warnings.append("raw probabilities are effectively constant")
    if calibrated_std <= 1e-6:
        warnings.append("calibrated probabilities are effectively constant")
    if raw_std > 0 and calibrated_std < raw_std * 0.25:
        warnings.append("calibrator compresses probability std by more than 75%")
    if not any(item["raw_range"] > 1e-6 for item in numerical.values()):
        warnings.append("numerical sensitivity is effectively zero")

    return {
        "symbol": symbol,
        "strategy": strategy,
        "interval": interval,
        "numerical": numerical,
        "symbol_probability_range": symbol["calibrated_range"],
        "strategy_probability_range": strategy["calibrated_range"],
        "interval_probability_range": interval["calibrated_range"],
        "raw_probability_std": raw_std,
        "calibrated_probability_std": calibrated_std,
        "calibration_compression_ratio": calibrated_std / raw_std if raw_std > 0 else None,
        "warnings": warnings,
    }


def main() -> int:
    import json

    from .model_registry import ModelRegistry, atomic_write_json
    from .training_config import TrainingConfig
    from .train_model import _catboost_frame, load_model_bundle

    config = TrainingConfig.from_env()
    registry = ModelRegistry(config)
    bundle = registry.active_bundle_dir()
    if bundle is None:
        raise RuntimeError("active model is not configured")
    if not config.dataset_path.exists():
        raise FileNotFoundError(f"dataset not found: {config.dataset_path}")
    dataset = pd.read_parquet(config.dataset_path)
    model, model_config, calibrator = load_model_bundle(bundle)
    report = build_sensitivity_report(
        model=model,
        calibrator=calibrator,
        frame=_catboost_frame(dataset.tail(min(len(dataset), 1000))),
        cat_features=list(model_config["cat_features"]),
        supported_symbols=list(model_config.get("supported_symbols", [])),
        supported_strategies=list(model_config.get("supported_strategies", [])),
        supported_intervals=list(model_config.get("supported_intervals", [])),
    )
    path = config.reports_path / "latest_sensitivity_report.json"
    atomic_write_json(report, path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"saved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

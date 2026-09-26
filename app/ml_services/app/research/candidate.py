from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import catboost
import joblib
import numpy as np
import pandas as pd
import sklearn

from ..training.model_registry import ModelRegistry, atomic_write_json, file_checksum, model_version_now
from ..training.prediction_sensitivity import build_sensitivity_report
from ..training.training_config import TrainingConfig
from .modeling import ResearchBundle, predict_bundle


def export_research_candidate(
    *,
    bundle: ResearchBundle,
    final_frame: pd.DataFrame,
    final_metrics: dict[str, Any],
    walk_forward: dict[str, Any],
    deployment_frame: pd.DataFrame | None = None,
    research_config: dict[str, Any],
    training: TrainingConfig,
    dataset_report: dict[str, Any],
    registry: ModelRegistry | None = None,
) -> dict[str, Any]:
    if bundle.architecture != "pooled":
        raise ValueError("only pooled research bundles can be exported to the current online architecture")
    if not bundle.feature_set.production_compatible:
        raise ValueError("research feature set is not available in online inference")
    if set(bundle.models) != {"__global__"}:
        raise ValueError("pooled bundle must have one global model")

    registry = registry or ModelRegistry(training)
    version = model_version_now()
    candidate_dir = registry.create_candidate_dir(version)
    model = bundle.models["__global__"]
    calibrator = bundle.calibrators.get("__global__")
    model_path = candidate_dir / "model.cbm"
    model.save_model(str(model_path))
    calibrator_name = None
    if calibrator is not None:
        calibrator_name = "calibrator.joblib"
        joblib.dump(calibrator, candidate_dir / calibrator_name)

    feature_columns = list(bundle.feature_set.columns)
    cat_features = list(bundle.feature_set.cat_features)
    deployment_frame = final_frame if deployment_frame is None else deployment_frame
    prepared = deployment_frame[feature_columns].copy()
    for column in cat_features:
        prepared[column] = prepared[column].astype(str)
    sensitivity = build_sensitivity_report(
        model=model,
        calibrator=calibrator,
        frame=prepared,
        cat_features=cat_features,
        supported_symbols=sorted(deployment_frame["symbol"].astype(str).unique().tolist()),
        supported_strategies=sorted(deployment_frame["strategy_name"].astype(str).unique().tolist()),
        supported_intervals=sorted(deployment_frame["interval"].astype(str).unique().tolist()),
    )

    target = research_config["target"]
    config_payload = {
        "model_version": version,
        "feature_schema_version": "v3",
        "threshold": float(bundle.thresholds.get("__global__", 0.5)),
        "thresholds_by_strategy": {str(k): float(v) for k, v in bundle.thresholds.items()},
        "feature_cols": feature_columns,
        "cat_features": cat_features,
        "supported_symbols": sorted(deployment_frame["symbol"].astype(str).unique().tolist()),
        "allow_unseen_symbols": False,
        "supported_strategies": sorted(deployment_frame["strategy_name"].astype(str).unique().tolist()),
        "supported_intervals": [training.interval],
        "supported_exchanges": [training.exchange],
        "model_status": "research_candidate",
        "target_horizon_minutes": int(target["horizon_minutes"]),
        "target_horizon_bars": int(target["horizon_minutes"] // 60),
        "target_horizon_bars_by_interval": {training.interval: int(target["horizon_minutes"] // 60)},
        "target_definition": target["definition"],
        "minimum_net_return": float(target.get("minimum_net_return", training.minimum_net_return)),
        "maximum_target_drawdown": float(target.get("maximum_drawdown", training.maximum_target_drawdown)),
        "fee": training.fee,
        "slippage": training.slippage,
        "risk_atr_stop_multiplier": float(target["atr_stop_multiplier"]),
        "risk_min_stop_loss_pct": training.risk_min_stop_loss_pct,
        "risk_reward_ratio": float(target["reward_ratio"]),
        "intrabar_priority": training.intrabar_priority,
        "entry_convention": "next_bar_open",
        "exit_convention": (
            "first_touch_tp_sl_then_timeout"
            if target["definition"] == "first_touch_atr_rr"
            else "horizon_bar_close"
        ),
        "evaluation_train_end": research_config.get("evaluation_train_end"),
        "evaluation_test_start": str(final_frame["timestamp"].min()),
        "evaluation_test_end": str(final_frame["timestamp"].max()),
        "production_train_start": research_config.get("production_train_start"),
        "production_train_end": research_config.get("production_train_end"),
        "train_start": research_config.get("production_train_start") or research_config.get("train_start"),
        "train_end": research_config.get("production_train_end") or research_config.get("evaluation_train_end"),
        "evaluation_model_metrics_only": True,
        "parameters": bundle.parameters,
        "research_seed": bundle.seed,
        "class_weight_mode": bundle.class_weight_mode,
        "calibrator": calibrator_name,
        "calibration_method": bundle.calibration_methods.get("__global__", "none"),
        "runtime_versions": {
            "python": platform.python_version(),
            "catboost": catboost.__version__,
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__,
        },
    }
    atomic_write_json(config_payload, candidate_dir / "config.json")
    config_payload["model_checksum"] = file_checksum(model_path)
    atomic_write_json(config_payload, candidate_dir / "config.json")

    model_info = final_metrics.setdefault("model", {})
    model_info["tree_count"] = int(getattr(model, "tree_count_", 0) or 0)
    try:
        model_info["best_iteration"] = int(model.get_best_iteration())
    except Exception:
        model_info["best_iteration"] = None
    try:
        importance = model.get_feature_importance()
        model_info["feature_importance"] = {
            name: float(value)
            for name, value in sorted(zip(feature_columns, importance), key=lambda pair: pair[1], reverse=True)
        }
    except Exception:
        model_info["feature_importance"] = {}

    portfolio = final_metrics.get("portfolio", {})
    training_report = {
        "model_version": version,
        "research_pipeline": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selected_target": target,
        "selected_feature_set": bundle.feature_set.name,
        "selected_architecture": bundle.architecture,
        "selected_parameters": bundle.parameters,
        "selected_seed": bundle.seed,
        "class_weight_mode": bundle.class_weight_mode,
        "selected_thresholds": bundle.thresholds,
        "calibration": bundle.calibration_methods,
        "test_metrics": final_metrics,
        "portfolio_backtest": {
            "filtered": portfolio.get("cost_1x", {}),
            "all_signal_baseline": portfolio.get("all_signals", {}),
            "cost_stress_1_5x": portfolio.get("cost_1_5x", {}),
            "cost_stress_2x": portfolio.get("cost_2x", {}),
        },
        "walk_forward": walk_forward,
        "sensitivity": sensitivity,
        "training_config": training.to_dict(),
        "research_config": research_config,
        "production_refit": {
            "model_has_separate_oos_metrics": False,
            "evaluation_metrics_belong_to_frozen_evaluation_model": True,
            "production_train_start": research_config.get("production_train_start"),
            "production_train_end": research_config.get("production_train_end"),
        },
    }
    atomic_write_json(final_metrics, candidate_dir / "metrics.json")
    atomic_write_json(training_report, candidate_dir / "training_report.json")
    atomic_write_json(sensitivity, candidate_dir / "sensitivity_report.json")
    atomic_write_json(dataset_report, candidate_dir / "dataset_report.json")
    atomic_write_json({"thresholds": bundle.thresholds}, candidate_dir / "threshold_table.json")
    atomic_write_json(model_info.get("feature_importance", {}), candidate_dir / "feature_importance.json")
    final_frame.to_parquet(candidate_dir / "evaluation_holdout.parquet", index=False)
    registry.register_candidate(version, candidate_dir, final_metrics, decision="trained")
    return {
        "version": version,
        "candidate_dir": str(candidate_dir),
        "config": config_payload,
        "sensitivity": sensitivity,
        "training_report": training_report,
    }

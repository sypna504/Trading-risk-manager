from __future__ import annotations

import json
import math
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import catboost
import joblib
import numpy as np
import pandas as pd
import sklearn
from catboost import CatBoostClassifier, Pool
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ..features_builder import CAT_FEATURES, FEATURE_COLUMNS
from .evaluate_model import (
    compute_permutation_importance,
    evaluate_predictions,
    expected_calibration_error,
    probability_statistics,
    trading_metrics,
)
from .model_registry import ModelRegistry, atomic_write_json, file_checksum, model_version_now
from .prediction_sensitivity import build_sensitivity_report
from .time_split import global_time_split, walk_forward_time_splits
from .training_config import TrainingConfig


def _catboost_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[FEATURE_COLUMNS].copy()
    for column in CAT_FEATURES:
        result[column] = result[column].astype(str)
    return result


def _pool(frame: pd.DataFrame, with_label: bool = True) -> Pool:
    return Pool(
        data=_catboost_frame(frame),
        label=frame["target_good_trade"] if with_label else None,
        cat_features=CAT_FEATURES,
    )


def _physical_purge(config: TrainingConfig) -> pd.Timedelta:
    return pd.Timedelta(minutes=config.purge_minutes)


def _partition_by_time(
    frame: pd.DataFrame,
    fractions: tuple[float, ...],
    purge: pd.Timedelta,
) -> list[pd.DataFrame]:
    timestamps = pd.Index(pd.to_datetime(frame["timestamp"]).drop_duplicates().sort_values())
    if len(timestamps) < 12:
        raise ValueError("validation requires at least 12 unique timestamps")
    boundaries = [int(len(timestamps) * fraction) for fraction in fractions]
    starts = [0, *boundaries]
    ends = [*boundaries, len(timestamps)]
    parts: list[pd.DataFrame] = []
    for index, (start, end) in enumerate(zip(starts, ends)):
        selected = timestamps[start:end]
        if index < len(ends) - 1 and end < len(timestamps):
            next_start = timestamps[end]
            purged = selected[selected < next_start - purge]
            if len(purged) > 0:
                selected = purged
            elif len(selected) > 1:
                selected = selected[:-1]
        part = frame[frame["timestamp"].isin(selected)].copy()
        parts.append(part)
    if any(part.empty for part in parts):
        raise ValueError("validation partitions are empty after physical purge")
    return parts


def _validation_parts(
    validation: pd.DataFrame,
    purge_bars: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Backward-compatible validation partition helper."""
    return tuple(
        _partition_by_time(
            validation,
            (0.50, 0.75),
            pd.Timedelta(hours=max(purge_bars, 0)),
        )
    )


def _class_weight_parameters(train: pd.DataFrame) -> dict[str, Any]:
    positive_rate = float(train["target_good_trade"].mean())
    if positive_rate < 0.30 or positive_rate > 0.70:
        return {"auto_class_weights": "Balanced"}
    return {}


def _fit_catboost(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
    parameters: dict[str, Any],
    config: TrainingConfig,
) -> CatBoostClassifier:
    model_parameters = {key: value for key, value in parameters.items() if key != "name"}
    model = CatBoostClassifier(
        **model_parameters,
        loss_function="Logloss",
        eval_metric="Logloss",
        custom_metric=["AUC", "PRAUC", "BrierScore"],
        verbose=False,
        allow_writing_files=False,
        **_class_weight_parameters(train),
    )
    model.fit(
        _pool(train),
        eval_set=_pool(evaluation),
        early_stopping_rounds=config.early_stopping_rounds,
        use_best_model=True,
    )
    return model


def _model_validation_report(
    model: CatBoostClassifier,
    evaluation: pd.DataFrame,
    config: TrainingConfig,
) -> dict[str, Any]:
    probabilities = model.predict_proba(_pool(evaluation, with_label=False))[:, 1]
    y_true = evaluation["target_good_trade"].to_numpy(dtype=int)
    stats = probability_statistics(probabilities, y_true)
    positive_rate = float(y_true.mean())
    if np.unique(y_true).size < 2:
        roc_auc = None
        pr_auc = None
        brier = float(brier_score_loss(y_true, probabilities))
        score = -brier
    else:
        roc_auc = float(roc_auc_score(y_true, probabilities))
        pr_auc = float(average_precision_score(y_true, probabilities))
        brier = float(brier_score_loss(y_true, probabilities))
        score = (
            1.5 * (roc_auc - 0.5)
            + 1.0 * (pr_auc - positive_rate)
            - 0.25 * brier
        )
    warnings: list[str] = []
    if float(stats.get("std") or 0.0) < config.minimum_probability_std:
        warnings.append("validation probability std is too low")
        score -= 1.0
    if float(stats.get("range") or 0.0) < config.minimum_probability_range:
        warnings.append("validation probability range is too low")
        score -= 1.0
    return {
        "score": float(score),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "positive_rate": positive_rate,
        "brier_score": brier,
        "probabilities": stats,
        "warnings": warnings,
        "best_iteration": int(model.get_best_iteration()),
        "tree_count": int(model.tree_count_),
    }


def _model_score(model: CatBoostClassifier, evaluation: pd.DataFrame) -> float:
    """Backward-compatible scalar validation score."""
    config = TrainingConfig()
    return float(_model_validation_report(model, evaluation, config)["score"])


def _fit_calibrator(
    probabilities: np.ndarray,
    y_true: np.ndarray,
    method: str,
):
    if method == "isotonic":
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(probabilities, y_true)
        return calibrator
    if method == "platt":
        calibrator = LogisticRegression(random_state=42)
        calibrator.fit(probabilities.reshape(-1, 1), y_true)
        return calibrator
    if method == "none":
        return None
    raise ValueError(f"unknown calibration method: {method}")


def apply_calibrator(calibrator: Any | None, probabilities: np.ndarray) -> np.ndarray:
    raw = np.asarray(probabilities, dtype=float)
    if calibrator is None:
        return raw
    if isinstance(calibrator, IsotonicRegression):
        return np.asarray(calibrator.predict(raw), dtype=float)
    return np.asarray(calibrator.predict_proba(raw.reshape(-1, 1))[:, 1], dtype=float)


def _calibration_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    clipped = np.clip(probabilities, 1e-9, 1 - 1e-9)
    return {
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "log_loss": float(log_loss(y_true, clipped, labels=[0, 1])),
        "expected_calibration_error": float(
            expected_calibration_error(y_true, probabilities)
        ),
        "probabilities": probability_statistics(probabilities, y_true),
    }


def choose_calibration(
    model: CatBoostClassifier,
    calibration: pd.DataFrame,
    selection: pd.DataFrame,
    config: TrainingConfig,
) -> tuple[Any | None, str, np.ndarray, dict[str, Any]]:
    selection_raw = model.predict_proba(_pool(selection, with_label=False))[:, 1]
    y_selection = selection["target_good_trade"].to_numpy(dtype=int)
    raw_metrics = _calibration_metrics(y_selection, selection_raw)
    candidates: list[dict[str, Any]] = [
        {
            "method": "none",
            "calibrator": None,
            "probabilities": selection_raw,
            "metrics": raw_metrics,
            "valid": True,
            "reason": None,
        }
    ]
    if (
        config.enable_calibration
        and not calibration.empty
        and calibration["target_good_trade"].nunique() == 2
        and selection["target_good_trade"].nunique() == 2
    ):
        calibration_raw = model.predict_proba(_pool(calibration, with_label=False))[:, 1]
        y_calibration = calibration["target_good_trade"].to_numpy(dtype=int)
        for method in config.calibration_methods:
            if method == "none":
                continue
            try:
                calibrator = _fit_calibrator(calibration_raw, y_calibration, method)
                probabilities = apply_calibrator(calibrator, selection_raw)
                metrics = _calibration_metrics(y_selection, probabilities)
                raw_std = float(raw_metrics["probabilities"]["std"] or 0.0)
                calibrated_std = float(metrics["probabilities"]["std"] or 0.0)
                valid = (
                    calibrated_std >= config.minimum_probability_std
                    and calibrated_std >= raw_std * config.minimum_calibrated_std_ratio
                    and int(metrics["probabilities"]["unique_count"] or 0)
                    >= config.minimum_unique_probabilities
                )
                candidates.append(
                    {
                        "method": method,
                        "calibrator": calibrator,
                        "probabilities": probabilities,
                        "metrics": metrics,
                        "valid": valid,
                        "reason": None if valid else "calibration compresses probabilities too much",
                    }
                )
            except Exception as error:
                candidates.append(
                    {
                        "method": method,
                        "calibrator": None,
                        "probabilities": selection_raw,
                        "metrics": {},
                        "valid": False,
                        "reason": str(error),
                    }
                )

    valid = [candidate for candidate in candidates if candidate["valid"]]
    best = min(valid, key=lambda item: item["metrics"]["brier_score"])
    improvement = raw_metrics["brier_score"] - best["metrics"]["brier_score"]
    if best["method"] != "none" and improvement < config.minimum_calibration_brier_improvement:
        best = candidates[0]
    report = {
        "selected_method": best["method"],
        "raw_metrics": raw_metrics,
        "candidates": [
            {
                "method": item["method"],
                "metrics": item["metrics"],
                "valid": item["valid"],
                "reason": item["reason"],
            }
            for item in candidates
        ],
        "brier_improvement": raw_metrics["brier_score"]
        - best["metrics"]["brier_score"],
    }
    return best["calibrator"], best["method"], best["probabilities"], report


def _choose_calibration(
    model: CatBoostClassifier,
    calibration: pd.DataFrame,
    threshold_frame: pd.DataFrame,
    config: TrainingConfig,
):
    """Backward-compatible three-value calibration API."""
    calibrator, method, probabilities, report = choose_calibration(
        model, calibration, threshold_frame, config
    )
    legacy_report = {
        "enabled": calibrator is not None,
        "method": method if calibrator is not None else None,
        "raw_brier": report.get("raw_metrics", {}).get("brier_score"),
        "calibrated_brier": next(
            (
                item.get("metrics", {}).get("brier_score")
                for item in report.get("candidates", [])
                if item.get("method") == method
            ),
            report.get("raw_metrics", {}).get("brier_score"),
        ),
    }
    return calibrator, probabilities, legacy_report


def _threshold_candidates(config: TrainingConfig) -> np.ndarray:
    return np.arange(
        config.threshold_min,
        config.threshold_max + config.threshold_step / 2,
        config.threshold_step,
    )


def select_threshold(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    config: TrainingConfig,
    minimum_trades: int | None = None,
) -> tuple[float, list[dict[str, Any]]]:
    required_trades = minimum_trades or config.minimum_selected_trades
    rows: list[dict[str, Any]] = []
    for threshold in _threshold_candidates(config):
        metrics = trading_metrics(frame, probabilities, float(threshold))
        trades = int(metrics["trades"])
        selected_rate = float(metrics["selected_rate"])
        mean_return = metrics["mean_net_return"]
        total_return = metrics["total_net_return"]
        max_drawdown = metrics["maximum_drawdown"]
        profit_factor = metrics["profit_factor"]
        valid = (
            trades >= required_trades
            and config.minimum_selected_rate <= selected_rate <= config.maximum_selected_rate
            and mean_return is not None
            and mean_return > 0
            and total_return is not None
            and total_return > 0
            and max_drawdown is not None
            and max_drawdown >= config.maximum_allowed_drawdown
            and profit_factor is not None
            and profit_factor > config.minimum_profit_factor
        )
        score = None
        if valid:
            score = float(
                total_return
                - 0.50 * abs(max_drawdown)
                + 0.10 * math.log(max(profit_factor, 1e-9))
                + 0.05 * float(metrics["win_rate"] or 0.0)
            )
        rows.append(
            {
                "threshold": float(threshold),
                "valid": valid,
                "score": score,
                "trades": trades,
                "selected_rate": selected_rate,
                "win_rate": metrics["win_rate"],
                "mean_net_return": mean_return,
                "total_net_return": total_return,
                "maximum_drawdown": max_drawdown,
                "profit_factor": profit_factor,
            }
        )
    valid_rows = [row for row in rows if row["valid"]]
    if valid_rows:
        best = max(valid_rows, key=lambda row: float(row["score"]))
        return float(best["threshold"]), rows
    fallback = min(
        rows,
        key=lambda row: (
            abs(float(row["selected_rate"]) - 0.20),
            -float(row["total_net_return"] if row["total_net_return"] is not None else -1e9),
        ),
    )
    return float(fallback["threshold"]), rows


def select_strategy_thresholds(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    config: TrainingConfig,
) -> tuple[dict[str, float], dict[str, Any]]:
    global_threshold, global_table = select_threshold(frame, probabilities, config)
    thresholds: dict[str, float] = {"__global__": global_threshold}
    report: dict[str, Any] = {"__global__": global_table}
    frame_with_probability = frame.copy()
    frame_with_probability["_probability"] = probabilities
    for strategy in config.supported_strategies:
        part = frame_with_probability[
            frame_with_probability["strategy_name"] == strategy
        ]
        if len(part) < max(config.minimum_strategy_selected_trades * 3, 50):
            thresholds[strategy] = global_threshold
            report[strategy] = {
                "fallback": "not enough validation rows",
                "rows": int(len(part)),
            }
            continue
        threshold, table = select_threshold(
            part,
            part["_probability"].to_numpy(dtype=float),
            config,
            minimum_trades=config.minimum_strategy_selected_trades,
        )
        thresholds[strategy] = threshold
        report[strategy] = table
    return thresholds, report


def _fit_logistic_baseline(train: pd.DataFrame):
    categorical = list(CAT_FEATURES)
    numeric = [column for column in FEATURE_COLUMNS if column not in categorical]
    transformer = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical,
            ),
        ]
    )
    model = Pipeline(
        [
            ("features", transformer),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(_catboost_frame(train), train["target_good_trade"])
    return model


def _baseline_reports(
    train: pd.DataFrame,
    threshold_frame: pd.DataFrame,
    test: pd.DataFrame | float | None = None,
    config: TrainingConfig | None = None,
) -> dict[str, Any]:
    if isinstance(test, (int, float)):
        fixed_threshold = float(test)
        test_frame = threshold_frame
        positive_rate = float(train["target_good_trade"].mean())
        constant = np.full(len(test_frame), positive_rate, dtype=float)
        reports = {"constant": evaluate_predictions(test_frame, constant, fixed_threshold)}
        try:
            logistic = _fit_logistic_baseline(train)
            probabilities = logistic.predict_proba(_catboost_frame(test_frame))[:, 1]
            reports["logistic_regression"] = evaluate_predictions(
                test_frame, probabilities, fixed_threshold
            )
        except Exception as error:
            reports["logistic_regression"] = {"error": str(error)}
        return reports
    if test is None:
        raise ValueError("test frame is required")
    config = config or TrainingConfig()
    reports: dict[str, Any] = {}
    positive_rate = float(train["target_good_trade"].mean())
    threshold_probs = np.full(len(threshold_frame), positive_rate, dtype=float)
    thresholds, _ = select_strategy_thresholds(threshold_frame, threshold_probs, config)
    test_probs = np.full(len(test), positive_rate, dtype=float)
    reports["constant"] = evaluate_predictions(test, test_probs, thresholds)
    try:
        logistic = _fit_logistic_baseline(train)
        validation_probs = logistic.predict_proba(_catboost_frame(threshold_frame))[:, 1]
        logistic_thresholds, _ = select_strategy_thresholds(
            threshold_frame, validation_probs, config
        )
        probabilities = logistic.predict_proba(_catboost_frame(test))[:, 1]
        reports["logistic_regression"] = evaluate_predictions(
            test, probabilities, logistic_thresholds
        )
    except Exception as error:
        reports["logistic_regression"] = {"error": str(error)}
    return reports


def _walk_forward_report(
    dataset: pd.DataFrame,
    *args,
) -> dict[str, Any]:
    config = next(
        (item for item in reversed(args) if isinstance(item, TrainingConfig)),
        TrainingConfig(),
    )
    folds = walk_forward_time_splits(
        dataset,
        folds=config.walk_forward_folds,
        minimum_fold_rows=config.minimum_fold_rows,
        purge_timedelta=_physical_purge(config),
    )
    results: list[dict[str, Any]] = []
    for index, (train, validation, test) in enumerate(folds):
        if train["target_good_trade"].nunique() < 2 or validation["target_good_trade"].nunique() < 2:
            results.append({"fold": index, "error": "train or validation has one class"})
            continue
        try:
            model_selection, threshold_frame = _partition_by_time(
                validation, (0.60,), _physical_purge(config)
            )
            best_model: CatBoostClassifier | None = None
            best_report: dict[str, Any] | None = None
            best_parameters: dict[str, Any] | None = None
            for parameters in config.model_search_space:
                model = _fit_catboost(train, model_selection, parameters, config)
                report = _model_validation_report(model, model_selection, config)
                if best_report is None or report["score"] > best_report["score"]:
                    best_model, best_report, best_parameters = model, report, parameters
            assert best_model is not None and best_parameters is not None
            validation_probabilities = best_model.predict_proba(
                _pool(threshold_frame, with_label=False)
            )[:, 1]
            thresholds, _ = select_strategy_thresholds(
                threshold_frame, validation_probabilities, config
            )
            test_probabilities = best_model.predict_proba(
                _pool(test, with_label=False)
            )[:, 1]
            metrics = evaluate_predictions(test, test_probabilities, thresholds)
            results.append(
                {
                    "fold": index,
                    "train_start": str(train["timestamp"].min()),
                    "train_end": str(train["timestamp"].max()),
                    "validation_start": str(validation["timestamp"].min()),
                    "validation_end": str(validation["timestamp"].max()),
                    "test_start": str(test["timestamp"].min()),
                    "test_end": str(test["timestamp"].max()),
                    "thresholds": thresholds,
                    "selected_parameters": best_parameters,
                    "metrics": metrics,
                }
            )
        except Exception as error:
            results.append({"fold": index, "error": str(error)})
    valid = [item for item in results if "metrics" in item]
    positive = [
        item
        for item in valid
        if float(item["metrics"]["trading"].get("total_net_return") or 0.0) > 0
    ]
    return {
        "folds": results,
        "completed_folds": len(valid),
        "positive_return_fold_rate": len(positive) / len(valid) if valid else None,
    }


def train_candidate(
    dataset: pd.DataFrame,
    config: TrainingConfig | None = None,
    registry: ModelRegistry | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    config = config or TrainingConfig.from_env()
    registry = registry or ModelRegistry(config)
    split = global_time_split(
        dataset,
        config.train_ratio,
        config.validation_ratio,
        config.test_ratio,
        purge_timedelta=_physical_purge(config),
    )
    train, validation, test = split.train, split.validation, split.test
    model_validation, calibration, threshold_frame = _partition_by_time(
        validation, (0.50, 0.75), _physical_purge(config)
    )
    if train["target_good_trade"].nunique() < 2:
        raise ValueError("train contains one class")
    if model_validation["target_good_trade"].nunique() < 2:
        raise ValueError("model-selection validation contains one class")

    model_trials: list[dict[str, Any]] = []
    best_model: CatBoostClassifier | None = None
    best_parameters: dict[str, Any] | None = None
    best_report: dict[str, Any] | None = None
    for parameters in config.model_search_space:
        model = _fit_catboost(train, model_validation, parameters, config)
        report = _model_validation_report(model, model_validation, config)
        model_trials.append({"name": parameters["name"], "parameters": parameters, **report})
        if best_report is None or report["score"] > best_report["score"]:
            best_model, best_parameters, best_report = model, parameters, report
    assert best_model is not None and best_parameters is not None and best_report is not None

    calibrator, calibration_method, threshold_probabilities, calibration_report = choose_calibration(
        best_model, calibration, threshold_frame, config
    )
    thresholds, threshold_report = select_strategy_thresholds(
        threshold_frame, threshold_probabilities, config
    )

    raw_test_probabilities = best_model.predict_proba(_pool(test, with_label=False))[:, 1]
    test_probabilities = apply_calibrator(calibrator, raw_test_probabilities)
    metrics = evaluate_predictions(
        test,
        test_probabilities,
        thresholds,
        model=best_model,
        feature_names=FEATURE_COLUMNS,
    )
    raw_metrics = evaluate_predictions(test, raw_test_probabilities, thresholds)
    if test["target_good_trade"].nunique() == 2:
        metrics.setdefault("model", {})["permutation_importance"] = compute_permutation_importance(
            best_model,
            _catboost_frame(test),
            test["target_good_trade"],
            FEATURE_COLUMNS,
            config.random_seed,
        )
    baseline_metrics = _baseline_reports(train, threshold_frame, test, config)
    walk_forward = _walk_forward_report(dataset, config)
    sensitivity_report = build_sensitivity_report(
        model=best_model,
        calibrator=calibrator,
        frame=_catboost_frame(test),
        cat_features=CAT_FEATURES,
        supported_symbols=sorted(dataset["symbol"].unique().tolist()),
        supported_strategies=config.supported_strategies,
        supported_intervals=config.supported_intervals,
    )

    version = model_version_now()
    candidate_dir = registry.create_candidate_dir(version)
    model_path = candidate_dir / "model.cbm"
    best_model.save_model(str(model_path))
    calibrator_filename = None
    if calibrator is not None:
        calibrator_filename = "calibrator.joblib"
        joblib.dump(calibrator, candidate_dir / calibrator_filename)

    config_payload = {
        "model_version": version,
        "feature_schema_version": config.feature_schema_version,
        "threshold": thresholds["__global__"],
        "thresholds_by_strategy": thresholds,
        "feature_cols": FEATURE_COLUMNS,
        "cat_features": CAT_FEATURES,
        "supported_symbols": sorted(dataset["symbol"].unique().tolist()),
        "allow_unseen_symbols": False,
        "supported_strategies": list(config.supported_strategies),
        "supported_intervals": list(config.supported_intervals),
        "target_horizon_minutes": config.target_horizon_minutes,
        "target_horizon_bars_by_interval": {
            config.interval: config.target_horizon_bars
        },
        "minimum_net_return": config.minimum_net_return,
        "maximum_target_drawdown": config.maximum_target_drawdown,
        "fee": config.fee,
        "slippage": config.slippage,
        "entry_convention": "next_bar_open",
        "exit_convention": "horizon_bar_close",
        "train_start": str(train["timestamp"].min()),
        "train_end": str(train["timestamp"].max()),
        "validation_start": str(validation["timestamp"].min()),
        "validation_end": str(validation["timestamp"].max()),
        "test_start": str(test["timestamp"].min()),
        "test_end": str(test["timestamp"].max()),
        "parameters": best_parameters,
        "calibrator": calibrator_filename,
        "calibration_method": calibration_method,
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
    atomic_write_json(metrics, candidate_dir / "metrics.json")
    atomic_write_json(raw_metrics, candidate_dir / "raw_metrics.json")
    atomic_write_json(sensitivity_report, candidate_dir / "sensitivity_report.json")
    atomic_write_json(threshold_report, candidate_dir / "threshold_table.json")
    atomic_write_json(
        metrics.get("model", {}).get("feature_importance", {}),
        candidate_dir / "feature_importance.json",
    )
    dataset_report = dataset.attrs.get("dataset_report", {})
    latest_dataset_report = config.reports_path / "latest_dataset_report.json"
    if not dataset_report and latest_dataset_report.exists():
        dataset_report = json.loads(latest_dataset_report.read_text(encoding="utf-8"))
    atomic_write_json(dataset_report, candidate_dir / "dataset_report.json")

    training_report = {
        "model_version": version,
        "start_time": started_at.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": time.perf_counter() - started_perf,
        "split": split.metadata,
        "model_trials": model_trials,
        "selected_parameters": best_parameters,
        "selected_model_validation": best_report,
        "selected_thresholds": thresholds,
        "calibration": calibration_report,
        "raw_test_metrics": raw_metrics,
        "test_metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "walk_forward": walk_forward,
        "sensitivity": sensitivity_report,
        "training_config": config.to_dict(),
    }
    atomic_write_json(training_report, candidate_dir / "training_report.json")
    registry.register_candidate(version, candidate_dir, metrics)
    return {
        "version": version,
        "candidate_dir": candidate_dir,
        "model": best_model,
        "calibrator": calibrator,
        "config": config_payload,
        "metrics": metrics,
        "training_report": training_report,
        "test_frame": test,
        "test_probabilities": test_probabilities,
    }


def load_model_bundle(bundle_dir: Path) -> tuple[CatBoostClassifier, dict[str, Any], Any | None]:
    configuration = json.loads((bundle_dir / "config.json").read_text(encoding="utf-8"))
    model = CatBoostClassifier()
    model.load_model(str(bundle_dir / "model.cbm"))
    calibrator = None
    calibrator_name = configuration.get("calibrator")
    if calibrator_name and (bundle_dir / calibrator_name).exists():
        calibrator = joblib.load(bundle_dir / calibrator_name)
    return model, configuration, calibrator


def evaluate_bundle_on_test(bundle_dir: Path, test: pd.DataFrame) -> dict[str, Any]:
    model, configuration, calibrator = load_model_bundle(bundle_dir)
    if configuration.get("feature_schema_version") != "v3":
        raise ValueError("champion uses an incompatible feature schema")
    feature_columns = configuration["feature_cols"]
    cat_features = configuration["cat_features"]
    features = test[feature_columns].copy()
    for column in cat_features:
        features[column] = features[column].astype(str)
    probabilities = model.predict_proba(Pool(features, cat_features=cat_features))[:, 1]
    probabilities = apply_calibrator(calibrator, probabilities)
    thresholds = configuration.get("thresholds_by_strategy") or float(
        configuration["threshold"]
    )
    return evaluate_predictions(
        test,
        probabilities,
        thresholds,
        model=model,
        feature_names=feature_columns,
    )


def train_model() -> None:
    config = TrainingConfig.from_env()
    dataset = pd.read_parquet(config.dataset_path)
    result = train_candidate(dataset, config=config)
    print(f"candidate saved: {result['candidate_dir']}")
    print(f"model version: {result['version']}")


if __name__ == "__main__":
    train_model()

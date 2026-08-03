from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ..features_builder import CAT_FEATURES, FEATURE_COLUMNS
from .evaluate_model import (
    compute_permutation_importance,
    evaluate_predictions,
    trading_metrics,
)
from .model_registry import ModelRegistry, atomic_write_json, file_checksum, model_version_now
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


def _validation_parts(
    validation: pd.DataFrame, purge_bars: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    timestamps = pd.Index(pd.to_datetime(validation["timestamp"]).drop_duplicates().sort_values())
    if len(timestamps) < 12:
        raise ValueError(
            "validation requires at least 12 unique timestamps for "
            "early-stopping, calibration and threshold partitions"
        )
    eval_end = max(int(len(timestamps) * 0.50), 1)
    calibration_end = max(int(len(timestamps) * 0.75), eval_end + 1)
    evaluation_times = timestamps[: max(eval_end - purge_bars, 0)]
    calibration_times = timestamps[
        eval_end : max(calibration_end - purge_bars, eval_end)
    ]
    threshold_times = timestamps[calibration_end:]
    evaluation = validation[validation["timestamp"].isin(evaluation_times)].copy()
    calibration = validation[validation["timestamp"].isin(calibration_times)].copy()
    threshold = validation[validation["timestamp"].isin(threshold_times)].copy()
    if threshold.empty:
        threshold = calibration.copy()
        calibration = validation.iloc[0:0].copy()
    return evaluation, calibration, threshold


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
        eval_metric="AUC",
        auto_class_weights="Balanced",
        random_seed=config.random_seed,
        verbose=False,
        allow_writing_files=False,
    )
    model.fit(
        _pool(train),
        eval_set=_pool(evaluation),
        early_stopping_rounds=config.early_stopping_rounds,
        use_best_model=True,
    )
    return model


def _model_score(model: CatBoostClassifier, evaluation: pd.DataFrame) -> float:
    probabilities = model.predict_proba(_pool(evaluation, with_label=False))[:, 1]
    y_true = evaluation["target_good_trade"].to_numpy(dtype=int)
    if np.unique(y_true).size < 2:
        return -float(brier_score_loss(y_true, probabilities))
    return float(roc_auc_score(y_true, probabilities))


def _fit_calibrator(
    probabilities: np.ndarray,
    y_true: np.ndarray,
    method: str,
):
    if method == "isotonic":
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(probabilities, y_true)
        return calibrator
    calibrator = LogisticRegression(random_state=42)
    calibrator.fit(probabilities.reshape(-1, 1), y_true)
    return calibrator


def apply_calibrator(calibrator: Any | None, probabilities: np.ndarray) -> np.ndarray:
    raw = np.asarray(probabilities, dtype=float)
    if calibrator is None:
        return raw
    if isinstance(calibrator, IsotonicRegression):
        return np.asarray(calibrator.predict(raw), dtype=float)
    return np.asarray(calibrator.predict_proba(raw.reshape(-1, 1))[:, 1], dtype=float)


def _choose_calibration(
    model: CatBoostClassifier,
    calibration: pd.DataFrame,
    threshold_frame: pd.DataFrame,
    config: TrainingConfig,
) -> tuple[Any | None, np.ndarray, dict[str, Any]]:
    threshold_raw = model.predict_proba(_pool(threshold_frame, with_label=False))[:, 1]
    report: dict[str, Any] = {"enabled": False, "method": None, "raw_brier": None, "calibrated_brier": None}
    if (
        not config.enable_calibration
        or calibration.empty
        or calibration["target_good_trade"].nunique() < 2
        or threshold_frame["target_good_trade"].nunique() < 2
    ):
        return None, threshold_raw, report

    calibration_raw = model.predict_proba(_pool(calibration, with_label=False))[:, 1]
    calibrator = _fit_calibrator(
        calibration_raw,
        calibration["target_good_trade"].to_numpy(dtype=int),
        config.calibration_method,
    )
    calibrated = apply_calibrator(calibrator, threshold_raw)
    y_threshold = threshold_frame["target_good_trade"].to_numpy(dtype=int)
    raw_brier = float(brier_score_loss(y_threshold, threshold_raw))
    calibrated_brier = float(brier_score_loss(y_threshold, calibrated))
    report.update(
        {
            "method": config.calibration_method,
            "raw_brier": raw_brier,
            "calibrated_brier": calibrated_brier,
            "enabled": calibrated_brier < raw_brier,
        }
    )
    return (calibrator, calibrated, report) if report["enabled"] else (None, threshold_raw, report)


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
) -> tuple[float, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for threshold in _threshold_candidates(config):
        metrics = trading_metrics(frame, probabilities, float(threshold))
        trades = int(metrics["trades"])
        selected_rate = float(metrics["selected_rate"])
        mean_return = metrics["mean_net_return"]
        total_return = metrics["total_net_return"]
        max_drawdown = metrics["maximum_drawdown"]
        valid = (
            trades >= config.minimum_selected_trades
            and config.minimum_selected_rate <= selected_rate <= config.maximum_selected_rate
            and mean_return is not None
            and mean_return > 0
            and total_return is not None
            and total_return > 0
            and max_drawdown is not None
            and max_drawdown >= config.maximum_allowed_drawdown
        )
        score = None
        if valid:
            score = float(
                total_return
                - 0.50 * abs(max_drawdown)
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
            }
        )

    valid_rows = [row for row in rows if row["valid"]]
    if valid_rows:
        best = max(valid_rows, key=lambda row: row["score"])
        return float(best["threshold"]), rows

    fallback = min(
        rows,
        key=lambda row: (
            abs(float(row["selected_rate"]) - 0.30),
            -float(row["total_net_return"] or -1e9),
        ),
    )
    return float(fallback["threshold"]), rows


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
                    max_iter=500,
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
    test: pd.DataFrame,
    threshold: float,
) -> dict[str, Any]:
    positive_rate = float(train["target_good_trade"].mean())
    constant_probabilities = np.full(len(test), positive_rate, dtype=float)
    reports: dict[str, Any] = {
        "constant": evaluate_predictions(test, constant_probabilities, threshold)
    }
    try:
        logistic = _fit_logistic_baseline(train)
        probabilities = logistic.predict_proba(_catboost_frame(test))[:, 1]
        reports["logistic_regression"] = evaluate_predictions(
            test, probabilities, threshold
        )
    except Exception as error:
        reports["logistic_regression"] = {"error": str(error)}
    return reports


def _walk_forward_report(
    dataset: pd.DataFrame,
    parameters: dict[str, Any],
    threshold: float,
    config: TrainingConfig,
) -> dict[str, Any]:
    del parameters, threshold  # each fold selects its own parameters and threshold
    folds = walk_forward_time_splits(
        dataset,
        folds=config.walk_forward_folds,
        minimum_fold_rows=config.minimum_fold_rows,
        purge_bars=config.purge_bars,
    )
    results: list[dict[str, Any]] = []
    for index, (train, validation, test) in enumerate(folds):
        if (
            train["target_good_trade"].nunique() < 2
            or validation["target_good_trade"].nunique() < 2
        ):
            results.append({"fold": index, "error": "train or validation has one class"})
            continue
        try:
            fold_model = None
            fold_parameters = None
            fold_score = -float("inf")
            for candidate_parameters in config.model_search_space:
                model = _fit_catboost(
                    train, validation, candidate_parameters, config
                )
                score = _model_score(model, validation)
                if score > fold_score:
                    fold_score = score
                    fold_model = model
                    fold_parameters = candidate_parameters

            assert fold_model is not None and fold_parameters is not None
            validation_probabilities = fold_model.predict_proba(
                _pool(validation, with_label=False)
            )[:, 1]
            fold_threshold, _ = select_threshold(
                validation, validation_probabilities, config
            )
            test_probabilities = fold_model.predict_proba(
                _pool(test, with_label=False)
            )[:, 1]
            metrics = evaluate_predictions(test, test_probabilities, fold_threshold)
            results.append(
                {
                    "fold": index,
                    "train_start": str(train["timestamp"].min()),
                    "train_end": str(train["timestamp"].max()),
                    "validation_start": str(validation["timestamp"].min()),
                    "validation_end": str(validation["timestamp"].max()),
                    "test_start": str(test["timestamp"].min()),
                    "test_end": str(test["timestamp"].max()),
                    "threshold": fold_threshold,
                    "selected_parameters": fold_parameters,
                    "metrics": metrics,
                }
            )
        except Exception as error:
            results.append({"fold": index, "error": str(error)})

    valid = [item for item in results if "metrics" in item]
    positive_improvements = [
        item
        for item in valid
        if (item["metrics"]["trading"].get("total_net_return") or 0.0) > 0
    ]
    return {
        "folds": results,
        "completed_folds": len(valid),
        "positive_return_fold_rate": (
            len(positive_improvements) / len(valid) if valid else None
        ),
    }


def train_candidate(
    dataset: pd.DataFrame,
    config: TrainingConfig | None = None,
    registry: ModelRegistry | None = None,
) -> dict[str, Any]:
    training_started_at = datetime.now(timezone.utc)
    training_started_perf = time.perf_counter()
    config = config or TrainingConfig.from_env()
    registry = registry or ModelRegistry(config)
    split = global_time_split(
        dataset,
        config.train_ratio,
        config.validation_ratio,
        config.test_ratio,
        config.purge_bars,
    )
    train, validation, test = split.train, split.validation, split.test
    model_validation, calibration, threshold_frame = _validation_parts(
        validation, config.purge_bars
    )

    if train["target_good_trade"].nunique() < 2:
        raise ValueError("train contains one class")
    if model_validation.empty or threshold_frame.empty:
        raise ValueError("validation partitions are empty")
    if model_validation["target_good_trade"].nunique() < 2:
        raise ValueError("model-selection validation contains one class")

    model_trials: list[dict[str, Any]] = []
    best_model: CatBoostClassifier | None = None
    best_parameters: dict[str, Any] | None = None
    best_score = -float("inf")

    for parameters in config.model_search_space:
        model = _fit_catboost(train, model_validation, parameters, config)
        score = _model_score(model, model_validation)
        model_trials.append(
            {
                "name": parameters["name"],
                "validation_score": score,
                "best_iteration": model.get_best_iteration(),
                "tree_count": int(model.tree_count_),
                "parameters": parameters,
            }
        )
        if score > best_score:
            best_score = score
            best_model = model
            best_parameters = parameters

    assert best_model is not None and best_parameters is not None
    calibrator, threshold_probabilities, calibration_report = _choose_calibration(
        best_model, calibration, threshold_frame, config
    )
    threshold, threshold_table = select_threshold(
        threshold_frame, threshold_probabilities, config
    )

    raw_test_probabilities = best_model.predict_proba(_pool(test, with_label=False))[:, 1]
    test_probabilities = apply_calibrator(calibrator, raw_test_probabilities)
    metrics = evaluate_predictions(
        test,
        test_probabilities,
        threshold,
        model=best_model,
        feature_names=FEATURE_COLUMNS,
    )
    if test["target_good_trade"].nunique() == 2:
        metrics.setdefault("model", {})["permutation_importance"] = (
            compute_permutation_importance(
                best_model,
                _catboost_frame(test),
                test["target_good_trade"],
                FEATURE_COLUMNS,
                config.random_seed,
            )
        )
    baseline_metrics = _baseline_reports(train, test, threshold)
    walk_forward = _walk_forward_report(dataset, best_parameters, threshold, config)

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
        "threshold": threshold,
        "feature_cols": FEATURE_COLUMNS,
        "cat_features": CAT_FEATURES,
        "train_start": str(train["timestamp"].min()),
        "train_end": str(train["timestamp"].max()),
        "validation_start": str(validation["timestamp"].min()),
        "validation_end": str(validation["timestamp"].max()),
        "test_start": str(test["timestamp"].min()),
        "test_end": str(test["timestamp"].max()),
        "parameters": best_parameters,
        "calibrator": calibrator_filename,
        "calibration_method": calibration_report.get("method") if calibrator is not None else None,
    }
    atomic_write_json(config_payload, candidate_dir / "config.json")
    config_payload["model_checksum"] = file_checksum(model_path)
    atomic_write_json(config_payload, candidate_dir / "config.json")
    atomic_write_json(metrics, candidate_dir / "metrics.json")
    atomic_write_json(
        metrics.get("model", {}).get("feature_importance", {}),
        candidate_dir / "feature_importance.json",
    )
    dataset_report = dataset.attrs.get("dataset_report", {})
    latest_dataset_report = config.reports_path / "latest_dataset_report.json"
    if not dataset_report and latest_dataset_report.exists():
        dataset_report = json.loads(
            latest_dataset_report.read_text(encoding="utf-8")
        )
    atomic_write_json(dataset_report, candidate_dir / "dataset_report.json")
    atomic_write_json(threshold_table, candidate_dir / "threshold_table.json")

    training_finished_at = datetime.now(timezone.utc)
    training_report = {
        "model_version": version,
        "start_time": training_started_at.isoformat(),
        "end_time": training_finished_at.isoformat(),
        "duration_seconds": time.perf_counter() - training_started_perf,
        "split": split.metadata,
        "model_trials": model_trials,
        "selected_parameters": best_parameters,
        "selected_threshold": threshold,
        "calibration": calibration_report,
        "test_metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "walk_forward": walk_forward,
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
    feature_columns = configuration["feature_cols"]
    cat_features = configuration["cat_features"]
    features = test[feature_columns].copy()
    for column in cat_features:
        features[column] = features[column].astype(str)
    probabilities = model.predict_proba(Pool(features, cat_features=cat_features))[:, 1]
    probabilities = apply_calibrator(calibrator, probabilities)
    return evaluate_predictions(
        test,
        probabilities,
        float(configuration["threshold"]),
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

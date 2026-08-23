from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

ThresholdSpec = float | dict[str, float]


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def threshold_array(frame: pd.DataFrame, threshold: ThresholdSpec) -> np.ndarray:
    if isinstance(threshold, dict):
        if "strategy_name" not in frame.columns:
            raise ValueError("strategy thresholds require strategy_name")
        fallback = float(threshold.get("__global__", 0.5))
        return np.asarray(
            [float(threshold.get(str(strategy), fallback)) for strategy in frame["strategy_name"]],
            dtype=float,
        )
    return np.full(len(frame), float(threshold), dtype=float)


def expected_calibration_error(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    bins: int = 10,
) -> float:
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        mask = (
            (probabilities >= left) & (probabilities <= right)
            if right == 1.0
            else (probabilities >= left) & (probabilities < right)
        )
        if not mask.any():
            continue
        ece += mask.mean() * abs(probabilities[mask].mean() - y_true[mask].mean())
    return float(ece)


def calibration_curve_points(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    bins: int = 10,
) -> list[dict[str, float | int]]:
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    points: list[dict[str, float | int]] = []
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        mask = (
            (probabilities >= left) & (probabilities <= right)
            if right == 1.0
            else (probabilities >= left) & (probabilities < right)
        )
        if mask.any():
            points.append(
                {
                    "left": float(left),
                    "right": float(right),
                    "count": int(mask.sum()),
                    "mean_probability": float(probabilities[mask].mean()),
                    "positive_rate": float(y_true[mask].mean()),
                }
            )
    return points


def probability_statistics(
    probabilities: np.ndarray,
    y_true: np.ndarray | None = None,
) -> dict[str, Any]:
    values = np.asarray(probabilities, dtype=float)
    result: dict[str, Any] = {
        "count": int(len(values)),
        "unique_count": int(np.unique(np.round(values, 12)).size),
        "min": _safe_float(np.min(values)) if len(values) else None,
        "max": _safe_float(np.max(values)) if len(values) else None,
        "mean": _safe_float(np.mean(values)) if len(values) else None,
        "std": _safe_float(np.std(values)) if len(values) else None,
        "range": _safe_float(np.ptp(values)) if len(values) else None,
        "q05": _safe_float(np.quantile(values, 0.05)) if len(values) else None,
        "q25": _safe_float(np.quantile(values, 0.25)) if len(values) else None,
        "median": _safe_float(np.quantile(values, 0.50)) if len(values) else None,
        "q75": _safe_float(np.quantile(values, 0.75)) if len(values) else None,
        "q95": _safe_float(np.quantile(values, 0.95)) if len(values) else None,
    }
    if y_true is not None and len(np.unique(y_true)) == 2:
        result["expected_calibration_error"] = expected_calibration_error(y_true, values)
        result["calibration_curve"] = calibration_curve_points(y_true, values)
    else:
        result["expected_calibration_error"] = None
        result["calibration_curve"] = []
    return result


def _max_drawdown_from_returns(returns: pd.Series) -> float:
    if returns.empty:
        return float("nan")
    equity = (1.0 + returns.clip(lower=-0.999999)).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min())


def _group_stability(
    selected: pd.DataFrame,
    group_column: str,
) -> dict[str, dict[str, float | int | None]]:
    if selected.empty or group_column not in selected.columns:
        return {}
    result: dict[str, dict[str, float | int | None]] = {}
    for key, part in selected.groupby(group_column):
        result[str(key)] = {
            "trades": int(len(part)),
            "win_rate": float((part["net_return"] > 0).mean()),
            "mean_net_return": _safe_float(part["net_return"].mean()),
            "total_net_return": _safe_float(part["net_return"].sum()),
        }
    return result


def trading_metrics(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    threshold: ThresholdSpec,
) -> dict[str, Any]:
    df = frame.copy()
    df["prob_good_trade"] = probabilities
    df["decision_threshold"] = threshold_array(df, threshold)
    selected = df[df["prob_good_trade"] >= df["decision_threshold"]].copy()

    threshold_payload: float | dict[str, float]
    threshold_payload = threshold if isinstance(threshold, dict) else float(threshold)
    if selected.empty:
        return {
            "threshold": threshold_payload,
            "trades": 0,
            "selected_rate": 0.0,
            "win_rate": None,
            "mean_net_return": None,
            "median_net_return": None,
            "total_net_return": 0.0,
            "cumulative_return": 0.0,
            "maximum_drawdown": None,
            "profit_factor": None,
            "average_win": None,
            "average_loss": None,
            "payoff_ratio": None,
            "sharpe_like": None,
            "by_month": {},
            "by_symbol": {},
            "by_strategy": {},
            "by_interval": {},
        }

    selected["timestamp"] = pd.to_datetime(selected["timestamp"])
    per_timestamp = selected.groupby("timestamp")["net_return"].sum().sort_index()
    cumulative_return = float((1.0 + per_timestamp.clip(lower=-0.999999)).prod() - 1.0)
    wins = selected.loc[selected["net_return"] > 0, "net_return"]
    losses = selected.loc[selected["net_return"] < 0, "net_return"]
    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    average_win = float(wins.mean()) if not wins.empty else None
    average_loss = float(losses.mean()) if not losses.empty else None
    payoff_ratio = (
        average_win / abs(average_loss)
        if average_win is not None and average_loss not in (None, 0.0)
        else None
    )
    std = float(per_timestamp.std()) if len(per_timestamp) > 1 else 0.0
    sharpe_like = (
        float(per_timestamp.mean() / std * np.sqrt(365 * 24)) if std > 0 else None
    )
    monthly = (
        selected.assign(month=selected["timestamp"].dt.to_period("M").astype(str))
        .groupby("month")["net_return"]
        .agg(["count", "mean", "sum"])
    )
    return {
        "threshold": threshold_payload,
        "trades": int(len(selected)),
        "selected_rate": float(len(selected) / len(df)),
        "win_rate": float((selected["net_return"] > 0).mean()),
        "mean_net_return": float(selected["net_return"].mean()),
        "median_net_return": float(selected["net_return"].median()),
        "total_net_return": float(selected["net_return"].sum()),
        "cumulative_return": cumulative_return,
        "maximum_drawdown": _max_drawdown_from_returns(per_timestamp),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "average_win": average_win,
        "average_loss": average_loss,
        "payoff_ratio": payoff_ratio,
        "sharpe_like": sharpe_like,
        "by_month": {
            str(index): {
                "trades": int(row["count"]),
                "mean_net_return": float(row["mean"]),
                "total_net_return": float(row["sum"]),
            }
            for index, row in monthly.iterrows()
        },
        "by_symbol": _group_stability(selected, "symbol"),
        "by_strategy": _group_stability(selected, "strategy_name"),
        "by_interval": _group_stability(selected, "interval"),
    }


def evaluate_predictions(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    threshold: ThresholdSpec,
    model: Any | None = None,
    feature_names: list[str] | None = None,
) -> dict[str, Any]:
    y_true = frame["target_good_trade"].to_numpy(dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    thresholds = threshold_array(frame, threshold)
    predictions = (probabilities >= thresholds).astype(int)
    unique_classes = np.unique(y_true)

    classification: dict[str, Any] = {
        "positive_class_rate": float(y_true.mean()) if len(y_true) else None,
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, predictions, labels=[0, 1]).tolist(),
        "roc_auc": None,
        "pr_auc": None,
        "log_loss": None,
        "brier_score": None,
        "single_class_test": len(unique_classes) < 2,
    }
    if len(unique_classes) == 2:
        clipped = np.clip(probabilities, 1e-9, 1 - 1e-9)
        classification.update(
            {
                "roc_auc": float(roc_auc_score(y_true, probabilities)),
                "pr_auc": float(average_precision_score(y_true, probabilities)),
                "log_loss": float(log_loss(y_true, clipped, labels=[0, 1])),
                "brier_score": float(brier_score_loss(y_true, probabilities)),
            }
        )

    model_info: dict[str, Any] = {}
    if model is not None:
        model_info["tree_count"] = int(getattr(model, "tree_count_", 0) or 0)
        try:
            model_info["best_iteration"] = int(model.get_best_iteration())
        except Exception:
            model_info["best_iteration"] = None
        if feature_names:
            try:
                importance = model.get_feature_importance()
                model_info["feature_importance"] = {
                    name: float(value)
                    for name, value in sorted(
                        zip(feature_names, importance),
                        key=lambda pair: pair[1],
                        reverse=True,
                    )
                }
            except Exception:
                model_info["feature_importance"] = {}

    return {
        "classification": classification,
        "probabilities": probability_statistics(probabilities, y_true),
        "trading": trading_metrics(frame, probabilities, threshold),
        "model": model_info,
    }


def compute_permutation_importance(
    estimator: Any,
    x: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
    random_seed: int,
    max_rows: int = 2000,
) -> dict[str, float]:
    if len(x) > max_rows:
        sampled = x.sample(max_rows, random_state=random_seed)
        y_sampled = y.loc[sampled.index]
    else:
        sampled = x
        y_sampled = y
    try:
        result = permutation_importance(
            estimator,
            sampled,
            y_sampled,
            n_repeats=3,
            random_state=random_seed,
            scoring="roc_auc",
        )
    except Exception:
        return {}
    return {
        name: float(value)
        for name, value in sorted(
            zip(feature_names, result.importances_mean),
            key=lambda pair: pair[1],
            reverse=True,
        )
    }

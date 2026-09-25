from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ..backtesting.simulator import run_portfolio_backtest
from ..training.evaluate_model import evaluate_predictions, expected_calibration_error, trading_metrics
from ..training.training_config import TrainingConfig
from .features import FeatureSet
from .splits import ResearchSplit


@dataclass(slots=True)
class ResearchBundle:
    architecture: str
    feature_set: FeatureSet
    models: dict[str, CatBoostClassifier]
    calibrators: dict[str, Any | None]
    calibration_methods: dict[str, str]
    thresholds: dict[str, float]
    class_weight_mode: str
    parameters: dict[str, Any]
    seed: int
    utility_reference: dict[str, dict[str, float | None]]



def _architecture_group_column(architecture: str) -> str | None:
    if architecture == "pooled":
        return None
    return {
        "separate_strategy": "strategy_name",
        "separate_symbol": "symbol",
        "separate_liquidity": "liquidity_bucket",
    }.get(architecture)

def _frame(frame: pd.DataFrame, feature_set: FeatureSet) -> pd.DataFrame:
    result = frame[list(feature_set.columns)].copy()
    for column in feature_set.cat_features:
        result[column] = result[column].astype(str)
    return result


def _pool(frame: pd.DataFrame, feature_set: FeatureSet, *, with_label: bool = True) -> Pool:
    return Pool(
        _frame(frame, feature_set),
        label=frame["target_good_trade"] if with_label else None,
        cat_features=list(feature_set.cat_features),
    )


def _class_weights(frame: pd.DataFrame, mode: str) -> dict[str, Any]:
    mode = mode.strip().lower()
    if mode == "none":
        return {}
    rate = float(frame["target_good_trade"].mean())
    if not 0 < rate < 1:
        return {}
    if mode == "balanced":
        return {"auto_class_weights": "Balanced"}
    if mode.startswith("positive_x"):
        factor = float(mode.split("positive_x", 1)[1])
        return {"class_weights": [1.0, factor]}
    raise ValueError(f"unknown class weight mode: {mode}")


def fit_catboost(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
    feature_set: FeatureSet,
    parameters: dict[str, Any],
    seed: int,
    class_weight_mode: str,
    training: TrainingConfig,
) -> CatBoostClassifier:
    params = {key: value for key, value in parameters.items() if key != "name"}
    model = CatBoostClassifier(
        **params,
        random_seed=seed,
        loss_function="Logloss",
        eval_metric="Logloss",
        custom_metric=["AUC", "PRAUC", "BrierScore"],
        verbose=False,
        allow_writing_files=False,
        **_class_weights(train, class_weight_mode),
    )
    model.fit(
        _pool(train, feature_set),
        eval_set=_pool(evaluation, feature_set),
        early_stopping_rounds=training.early_stopping_rounds,
        use_best_model=True,
    )
    return model


def _predict_models(
    models: dict[str, CatBoostClassifier],
    frame: pd.DataFrame,
    feature_set: FeatureSet,
    architecture: str,
) -> np.ndarray:
    result = np.full(len(frame), np.nan, dtype=float)
    if architecture == "pooled":
        result[:] = models["__global__"].predict_proba(_pool(frame, feature_set, with_label=False))[:, 1]
        return result
    group_column = _architecture_group_column(architecture)
    if group_column is None or group_column not in frame.columns:
        raise ValueError(f"unknown or unavailable architecture grouping: {architecture}")
    fallback = models.get("__fallback__")
    if fallback is not None:
        result[:] = fallback.predict_proba(_pool(frame, feature_set, with_label=False))[:, 1]
    for group_value, model in models.items():
        if group_value == "__fallback__":
            continue
        mask = frame[group_column].astype(str).eq(group_value).to_numpy()
        if not mask.any():
            continue
        subset = frame.loc[mask]
        result[mask] = model.predict_proba(_pool(subset, feature_set, with_label=False))[:, 1]
    if np.isnan(result).any():
        missing = sorted(frame.loc[np.isnan(result), group_column].astype(str).unique().tolist())
        raise ValueError(f"separate architecture has no model or fallback for {group_column}: {missing}")
    return result


def fit_models(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
    feature_set: FeatureSet,
    parameters: dict[str, Any],
    seed: int,
    class_weight_mode: str,
    architecture: str,
    training: TrainingConfig,
) -> dict[str, CatBoostClassifier]:
    if architecture == "pooled":
        return {
            "__global__": fit_catboost(
                train, evaluation, feature_set, parameters, seed, class_weight_mode, training
            )
        }
    group_column = _architecture_group_column(architecture)
    if group_column is None or group_column not in train.columns or group_column not in evaluation.columns:
        raise ValueError(f"unknown or unavailable architecture grouping: {architecture}")
    models: dict[str, CatBoostClassifier] = {
        "__fallback__": fit_catboost(
            train, evaluation, feature_set, parameters, seed, class_weight_mode, training
        )
    }
    values = sorted(set(train[group_column].astype(str)) & set(evaluation[group_column].astype(str)))
    minimum_train = 300 if architecture == "separate_symbol" else 100
    minimum_eval = 50 if architecture == "separate_symbol" else 30
    for value in values:
        train_part = train[train[group_column].astype(str) == value]
        eval_part = evaluation[evaluation[group_column].astype(str) == value]
        if len(train_part) < minimum_train or len(eval_part) < minimum_eval:
            continue
        if train_part["target_good_trade"].nunique() < 2 or eval_part["target_good_trade"].nunique() < 2:
            continue
        models[value] = fit_catboost(
            train_part, eval_part, feature_set, parameters, seed, class_weight_mode, training
        )
    return models



def estimate_utility_reference(frame: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    """Estimate winner/loser payoffs using selection data only.

    These estimates are later applied to untouched OOS probabilities.  No test
    outcome is used to derive the expected-utility score.
    """
    result: dict[str, dict[str, float | None]] = {}
    groups: list[tuple[str, pd.DataFrame]] = [("__global__", frame)]
    groups.extend((str(name), part) for name, part in frame.groupby("strategy_name"))
    for name, part in groups:
        positive = part.loc[part["target_good_trade"].astype(int) == 1, "net_return"]
        negative = part.loc[part["target_good_trade"].astype(int) == 0, "net_return"]
        result[name] = {
            "expected_win": float(positive.mean()) if len(positive) else None,
            "expected_loss": float(negative.mean()) if len(negative) else None,
            "rows": int(len(part)),
        }
    return result


def expected_utility_diagnostics(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    reference: dict[str, dict[str, float | None]],
    training: TrainingConfig,
) -> dict[str, Any]:
    probabilities = np.asarray(probabilities, dtype=float)
    values = np.full(len(frame), np.nan, dtype=float)
    for index, strategy in enumerate(frame["strategy_name"].astype(str)):
        stats = reference.get(strategy) or reference.get("__global__", {})
        win = stats.get("expected_win")
        loss = stats.get("expected_loss")
        if win is None or loss is None:
            continue
        values[index] = probabilities[index] * float(win) + (1.0 - probabilities[index]) * float(loss)
    valid = np.isfinite(values)
    selected = valid & (values > 0.0)
    realized = frame.reset_index(drop=True).loc[selected]
    wins = realized.loc[realized["net_return"] > 0, "net_return"].sum() if len(realized) else 0.0
    losses = abs(realized.loc[realized["net_return"] < 0, "net_return"].sum()) if len(realized) else 0.0
    pseudo_probabilities = np.where(selected, 1.0, 0.0)
    portfolio = run_portfolio_backtest(
        frame,
        pseudo_probabilities,
        0.5,
        **_backtest_kwargs(training),
    )
    return {
        "reference": reference,
        "valid_rows": int(valid.sum()),
        "selected_rows": int(selected.sum()),
        "mean_expected_utility": float(np.nanmean(values)) if valid.any() else None,
        "mean_realized_net_return": float(realized["net_return"].mean()) if len(realized) else None,
        "total_realized_net_return": float(realized["net_return"].sum()) if len(realized) else 0.0,
        "profit_factor": float(wins / losses) if losses > 0 else (float("inf") if wins > 0 else None),
        "portfolio": portfolio,
    }

def probability_rank_diagnostics(frame: pd.DataFrame, probabilities: np.ndarray) -> dict[str, Any]:
    df = frame.copy().reset_index(drop=True)
    df["probability"] = np.asarray(probabilities, dtype=float)
    baseline = float(df["target_good_trade"].mean()) if len(df) else 0.0
    output: dict[str, Any] = {"positive_rate_baseline": baseline, "top_buckets": {}}
    for fraction in (0.01, 0.02, 0.05, 0.10, 0.20):
        count = max(int(math.ceil(len(df) * fraction)), 1)
        top = df.nlargest(count, "probability")
        wins = top.loc[top["net_return"] > 0, "net_return"].sum()
        losses = abs(top.loc[top["net_return"] < 0, "net_return"].sum())
        rate = float(top["target_good_trade"].mean()) if len(top) else None
        output["top_buckets"][f"top_{int(fraction * 100)}pct"] = {
            "observations": int(len(top)),
            "positive_rate": rate,
            "lift_over_baseline": rate / baseline if rate is not None and baseline > 0 else None,
            "mean_net_return": float(top["net_return"].mean()) if len(top) else None,
            "total_net_return": float(top["net_return"].sum()) if len(top) else 0.0,
            "profit_factor": float(wins / losses) if losses > 0 else (float("inf") if wins > 0 else None),
        }
    return output


def validation_score(frame: pd.DataFrame, probabilities: np.ndarray) -> dict[str, Any]:
    y = frame["target_good_trade"].to_numpy(dtype=int)
    baseline = float(y.mean())
    roc = float(roc_auc_score(y, probabilities)) if np.unique(y).size == 2 else None
    pr = float(average_precision_score(y, probabilities)) if np.unique(y).size == 2 else None
    brier = float(brier_score_loss(y, probabilities))
    rank = probability_rank_diagnostics(frame, probabilities)
    top10 = rank["top_buckets"]["top_10pct"]
    top10_mean = float(top10.get("mean_net_return") or 0.0)
    top10_pf = top10.get("profit_factor")
    finite_pf = float(top10_pf) if top10_pf is not None and math.isfinite(float(top10_pf)) else 3.0 if top10_pf else 0.0
    pr_lift = float(pr - baseline) if pr is not None else -1.0
    auc_edge = float(roc - 0.5) if roc is not None else -1.0
    # Model selection remains validation-only. Economic ranking is deliberately
    # weighted above classification metrics.
    score = 120.0 * top10_mean + 0.35 * min(finite_pf - 1.0, 2.0) + 1.0 * pr_lift + 0.25 * auc_edge - 0.10 * brier
    return {
        "score": float(score),
        "roc_auc": roc,
        "pr_auc": pr,
        "pr_baseline": baseline,
        "pr_lift": pr_lift,
        "brier": brier,
        "top_rank": rank,
    }


def _fit_calibrator(raw: np.ndarray, y: np.ndarray, method: str):
    if method == "none":
        return None
    if method == "platt":
        model = LogisticRegression(random_state=42)
        model.fit(raw.reshape(-1, 1), y)
        return model
    if method == "isotonic":
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(raw, y)
        return model
    raise ValueError(method)


def _apply_calibrator(calibrator: Any | None, raw: np.ndarray) -> np.ndarray:
    if calibrator is None:
        return np.asarray(raw, dtype=float)
    if isinstance(calibrator, IsotonicRegression):
        return np.asarray(calibrator.predict(raw), dtype=float)
    return np.asarray(calibrator.predict_proba(np.asarray(raw).reshape(-1, 1))[:, 1], dtype=float)


def choose_calibrators(
    models: dict[str, CatBoostClassifier],
    fit_frame: pd.DataFrame,
    selection_frame: pd.DataFrame,
    feature_set: FeatureSet,
    architecture: str,
    methods: list[str],
) -> tuple[dict[str, Any | None], dict[str, str], dict[str, Any]]:
    calibrators: dict[str, Any | None] = {}
    selected_methods: dict[str, str] = {}
    report: dict[str, Any] = {}
    keys = ["__global__"] if architecture == "pooled" else sorted(models)
    group_column = _architecture_group_column(architecture)
    for key in keys:
        fit_part = fit_frame if key in {"__global__", "__fallback__"} else fit_frame[fit_frame[group_column].astype(str) == key]
        sel_part = selection_frame if key in {"__global__", "__fallback__"} else selection_frame[selection_frame[group_column].astype(str) == key]
        if fit_part.empty or sel_part.empty:
            calibrators[key] = None
            selected_methods[key] = "none"
            report[key] = {"selected": "none", "reason": "empty calibration partition"}
            continue
        model = models[key]
        fit_raw = model.predict_proba(_pool(fit_part, feature_set, with_label=False))[:, 1]
        sel_raw = model.predict_proba(_pool(sel_part, feature_set, with_label=False))[:, 1]
        y_fit = fit_part["target_good_trade"].to_numpy(dtype=int)
        y_sel = sel_part["target_good_trade"].to_numpy(dtype=int)
        candidates: list[dict[str, Any]] = []
        for method in methods:
            if method != "none" and (np.unique(y_fit).size < 2 or np.unique(y_sel).size < 2):
                continue
            try:
                calibrator = _fit_calibrator(fit_raw, y_fit, method)
                probs = _apply_calibrator(calibrator, sel_raw)
                std = float(np.std(probs))
                unique = int(np.unique(np.round(probs, 12)).size)
                candidates.append(
                    {
                        "method": method,
                        "calibrator": calibrator,
                        "brier": float(brier_score_loss(y_sel, probs)),
                        "ece": float(expected_calibration_error(y_sel, probs)) if np.unique(y_sel).size == 2 else None,
                        "std": std,
                        "unique": unique,
                        "valid": std >= 0.005 and unique >= min(20, max(len(sel_part) // 4, 2)),
                    }
                )
            except Exception as error:
                candidates.append({"method": method, "calibrator": None, "valid": False, "error": str(error)})
        valid = [item for item in candidates if item.get("valid")]
        if not valid:
            chosen = next((item for item in candidates if item.get("method") == "none"), {"method": "none", "calibrator": None})
        else:
            chosen = min(valid, key=lambda item: float(item["brier"]))
        calibrators[key] = chosen.get("calibrator")
        selected_methods[key] = str(chosen["method"])
        report[key] = {
            "selected": chosen["method"],
            "candidates": [{k: v for k, v in item.items() if k != "calibrator"} for item in candidates],
        }
    return calibrators, selected_methods, report


def predict_bundle_raw(bundle: ResearchBundle, frame: pd.DataFrame) -> np.ndarray:
    return _predict_models(bundle.models, frame, bundle.feature_set, bundle.architecture)


def predict_bundle(bundle: ResearchBundle, frame: pd.DataFrame) -> np.ndarray:
    raw = predict_bundle_raw(bundle, frame)
    if bundle.architecture == "pooled":
        return _apply_calibrator(bundle.calibrators.get("__global__"), raw)
    group_column = _architecture_group_column(bundle.architecture)
    if group_column is None or group_column not in frame.columns:
        raise ValueError(f"unavailable calibration grouping for {bundle.architecture}")
    result = _apply_calibrator(bundle.calibrators.get("__fallback__"), raw)
    for group_value in bundle.models:
        if group_value == "__fallback__":
            continue
        mask = frame[group_column].astype(str).eq(group_value).to_numpy()
        result[mask] = _apply_calibrator(bundle.calibrators.get(group_value), raw[mask])
    return result


def _backtest_kwargs(training: TrainingConfig) -> dict[str, Any]:
    return {
        "interval": training.interval,
        "starting_capital": training.backtest_starting_capital,
        "risk_per_trade_pct": training.backtest_risk_per_trade_pct,
        "max_position_share_pct": training.backtest_max_position_share_pct,
        "max_concurrent_positions": training.backtest_max_concurrent_positions,
        "max_portfolio_risk_pct": training.backtest_max_portfolio_risk_pct,
        "max_gross_exposure_pct": training.backtest_max_gross_exposure_pct,
        "base_round_trip_cost": 2 * (training.fee + training.slippage),
    }


def _threshold_grid() -> np.ndarray:
    return np.arange(0.10, 0.91, 0.02)


def _candidate_threshold_rows(frame: pd.DataFrame, probabilities: np.ndarray, training: TrainingConfig, minimum_trades: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for threshold in _threshold_grid():
        trade = trading_metrics(frame, probabilities, float(threshold))
        if int(trade["trades"]) < minimum_trades:
            continue
        if trade["mean_net_return"] is None or trade["profit_factor"] is None:
            continue
        portfolio = run_portfolio_backtest(frame, probabilities, float(threshold), **_backtest_kwargs(training))
        score = (
            5.0 * float(portfolio["portfolio_return"])
            + 0.25 * min(float(portfolio.get("profit_factor") or 0.0) - 1.0, 2.0)
            + 0.10 * max(float(portfolio.get("sharpe") or 0.0), -3.0)
            - 1.0 * abs(min(float(portfolio.get("maximum_drawdown") or 0.0), 0.0))
        )
        rows.append({"threshold": float(threshold), "score": float(score), "trading": trade, "portfolio": portfolio})
    return rows


def select_economic_thresholds(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    training: TrainingConfig,
) -> tuple[dict[str, float], dict[str, Any]]:
    minimum_global = min(training.minimum_selected_trades, max(15, len(frame) // 100))
    global_rows = _candidate_threshold_rows(frame, probabilities, training, minimum_global)
    if not global_rows:
        global_threshold = 0.5
        global_best = {"threshold": global_threshold, "score": -999.0, "reason": "no valid economic threshold"}
    else:
        global_best = max(global_rows, key=lambda item: item["score"])
        global_threshold = float(global_best["threshold"])

    strategy_thresholds = {"__global__": global_threshold}
    strategy_report: dict[str, Any] = {}
    for strategy in sorted(frame["strategy_name"].astype(str).unique()):
        mask = frame["strategy_name"].astype(str).eq(strategy).to_numpy()
        part = frame.loc[mask]
        part_prob = np.asarray(probabilities)[mask]
        minimum = min(training.minimum_strategy_selected_trades, max(8, len(part) // 100))
        rows = _candidate_threshold_rows(part, part_prob, training, minimum)
        if rows:
            best = max(rows, key=lambda item: item["score"])
            strategy_thresholds[strategy] = float(best["threshold"])
            strategy_report[strategy] = best
        else:
            strategy_thresholds[strategy] = global_threshold
            strategy_report[strategy] = {"threshold": global_threshold, "reason": "fallback to global"}

    global_portfolio = run_portfolio_backtest(frame, probabilities, global_threshold, **_backtest_kwargs(training))
    strategy_portfolio = run_portfolio_backtest(frame, probabilities, strategy_thresholds, **_backtest_kwargs(training))
    chosen = strategy_thresholds if float(strategy_portfolio["portfolio_return"]) > float(global_portfolio["portfolio_return"]) else {"__global__": global_threshold}
    return chosen, {
        "global_best": global_best,
        "global_portfolio": global_portfolio,
        "strategy_thresholds": strategy_report,
        "strategy_portfolio": strategy_portfolio,
        "selected": "strategy_specific" if len(chosen) > 1 else "global",
    }


def build_bundle(
    split: ResearchSplit,
    feature_set: FeatureSet,
    parameters: dict[str, Any],
    seed: int,
    class_weight_mode: str,
    architecture: str,
    training: TrainingConfig,
) -> tuple[ResearchBundle, dict[str, Any]]:
    models = fit_models(
        split.train,
        split.model_selection,
        feature_set,
        parameters,
        seed,
        class_weight_mode,
        architecture,
        training,
    )
    model_selection_raw = _predict_models(models, split.model_selection, feature_set, architecture)
    selection_report = validation_score(split.model_selection, model_selection_raw)
    calibrators, methods, calibration_report = choose_calibrators(
        models,
        split.calibration_fit,
        split.calibration_selection,
        feature_set,
        architecture,
        training.calibration_methods,
    )
    partial = ResearchBundle(
        architecture=architecture,
        feature_set=feature_set,
        models=models,
        calibrators=calibrators,
        calibration_methods=methods,
        thresholds={"__global__": 0.5},
        class_weight_mode=class_weight_mode,
        parameters=parameters,
        seed=seed,
        utility_reference=estimate_utility_reference(split.threshold_selection),
    )
    threshold_probs = predict_bundle(partial, split.threshold_selection)
    thresholds, threshold_report = select_economic_thresholds(split.threshold_selection, threshold_probs, training)
    partial.thresholds = thresholds
    return partial, {
        "model_selection": selection_report,
        "calibration": calibration_report,
        "threshold_selection": threshold_report,
    }


def evaluate_bundle(bundle: ResearchBundle, frame: pd.DataFrame, training: TrainingConfig) -> dict[str, Any]:
    raw = predict_bundle_raw(bundle, frame)
    probabilities = predict_bundle(bundle, frame)
    metrics = evaluate_predictions(frame, probabilities, bundle.thresholds)
    metrics["raw_probability_diagnostics"] = probability_rank_diagnostics(frame, raw)
    metrics["probability_rank_diagnostics"] = probability_rank_diagnostics(frame, probabilities)
    metrics["expected_utility"] = expected_utility_diagnostics(
        frame, probabilities, bundle.utility_reference, training
    )
    kwargs = _backtest_kwargs(training)
    metrics["portfolio"] = {
        "cost_1x": run_portfolio_backtest(frame, probabilities, bundle.thresholds, cost_multiplier=1.0, **kwargs),
        "cost_1_5x": run_portfolio_backtest(frame, probabilities, bundle.thresholds, cost_multiplier=1.5, **kwargs),
        "cost_2x": run_portfolio_backtest(frame, probabilities, bundle.thresholds, cost_multiplier=2.0, **kwargs),
        "cost_3x": run_portfolio_backtest(frame, probabilities, bundle.thresholds, cost_multiplier=3.0, **kwargs),
        "all_signals": run_portfolio_backtest(frame, None, bundle.thresholds, trade_all_signals=True, **kwargs),
    }
    return metrics


def economic_score(metrics: dict[str, Any]) -> float:
    portfolio = metrics.get("portfolio", {})
    base = portfolio.get("cost_1x", {})
    stress = portfolio.get("cost_1_5x", {})
    stress2 = portfolio.get("cost_2x", {})
    classification = metrics.get("classification", {})
    pr = classification.get("pr_auc")
    baseline = classification.get("positive_class_rate")
    pr_lift = (float(pr) - float(baseline)) if pr is not None and baseline is not None else -1.0
    return float(
        6.0 * float(base.get("portfolio_return") or 0.0)
        + 3.0 * float(stress.get("portfolio_return") or 0.0)
        + 1.0 * float(stress2.get("portfolio_return") or 0.0)
        + 0.3 * min(float(base.get("profit_factor") or 0.0) - 1.0, 2.0)
        + 0.5 * pr_lift
        - 1.5 * abs(min(float(base.get("maximum_drawdown") or 0.0), 0.0))
    )


def explain_pooled_bundle(
    bundle: ResearchBundle,
    frame: pd.DataFrame,
    *,
    max_rows: int = 1000,
    permutation_repeats: int = 2,
) -> dict[str, Any]:
    """CatBoost importance, SHAP and validation-style permutation importance.

    This is intended only after the candidate has already passed economic
    robustness checks.  Permutations are evaluated on the frozen OOS frame and
    are explanatory; they are never fed back into selection in the same run.
    """
    if bundle.architecture != "pooled" or set(bundle.models) != {"__global__"}:
        return {"status": "not_run", "reason": "explanations require pooled bundle"}
    sample = frame.sort_values("timestamp").copy()
    if len(sample) > max_rows:
        positions = np.linspace(0, len(sample) - 1, max_rows, dtype=int)
        sample = sample.iloc[positions].copy()
    model = bundle.models["__global__"]
    feature_names = list(bundle.feature_set.columns)
    report: dict[str, Any] = {"rows": int(len(sample))}
    try:
        values = model.get_feature_importance()
        report["catboost_importance"] = {
            name: float(value)
            for name, value in sorted(zip(feature_names, values), key=lambda pair: pair[1], reverse=True)
        }
    except Exception as error:
        report["catboost_importance_error"] = str(error)
    try:
        shap = np.asarray(
            model.get_feature_importance(_pool(sample, bundle.feature_set, with_label=False), type="ShapValues")
        )
        mean_abs = np.mean(np.abs(shap[:, :-1]), axis=0)
        report["shap_mean_abs"] = {
            name: float(value)
            for name, value in sorted(zip(feature_names, mean_abs), key=lambda pair: pair[1], reverse=True)
        }
    except Exception as error:
        report["shap_error"] = str(error)

    y = sample["target_good_trade"].to_numpy(dtype=int)
    if np.unique(y).size < 2:
        report["permutation_importance"] = {"status": "not_run", "reason": "OOS sample has one class"}
        return report
    baseline = predict_bundle(bundle, sample)
    base_pr = float(average_precision_score(y, baseline))
    rng = np.random.default_rng(bundle.seed + 991)
    permutation: dict[str, dict[str, float]] = {}
    for feature in feature_names:
        drops: list[float] = []
        for _ in range(max(permutation_repeats, 1)):
            permuted = sample.copy()
            values = permuted[feature].to_numpy(copy=True)
            rng.shuffle(values)
            permuted[feature] = values
            probability = predict_bundle(bundle, permuted)
            drops.append(base_pr - float(average_precision_score(y, probability)))
        permutation[feature] = {
            "pr_auc_drop_mean": float(np.mean(drops)),
            "pr_auc_drop_std": float(np.std(drops)),
        }
    report["permutation_importance"] = dict(
        sorted(permutation.items(), key=lambda item: item[1]["pr_auc_drop_mean"], reverse=True)
    )
    return report

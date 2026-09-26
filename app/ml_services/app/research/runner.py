from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import pandas as pd

from ..backtesting.simulator import run_portfolio_backtest
from ..training.build_dataset import build_dataset
from ..training.model_registry import atomic_write_json
from ..training.statistical_validation import block_bootstrap_report
from ..training.target_config import physical_purge
from ..training.time_split import walk_forward_time_splits
from ..training.training_config import TrainingConfig
from ..training.train_model import _baseline_reports
from ..training.update_history import update_history
from .candidate import export_research_candidate
from .config import ResearchConfig, TargetExperiment
from .data import audit_history, dataframe_sha256, sha256_file
from .features import FeatureSet, augment_market_context, drop_incomplete, feature_sets
from .modeling import (
    ResearchBundle,
    build_bundle,
    economic_score,
    evaluate_bundle,
    explain_pooled_bundle,
    predict_bundle,
)
from .reports import atomic_json, atomic_text, experiment_table, fmt, header
from .progress import ResearchProgress
from .regression import evaluate_regression_bundle, fit_regression_bundle, regression_economic_score
from .splits import ResearchSplit, split_deployment_dataset, split_research_dataset, split_walk_forward_fold


SOURCE_REF = "feature/auto-signal-choseing + research patch"
_PROGRESS: ResearchProgress | None = None


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "NOT CAPTURED"


def _metric_row(
    *,
    experiment_id: str,
    phase: str,
    target: str,
    feature_set: str,
    architecture: str,
    class_weight: str,
    parameters: dict[str, Any] | None,
    seed: int | None,
    metrics: dict[str, Any] | None,
    score: float | None,
    error: str | None = None,
) -> dict[str, Any]:
    metrics = metrics or {}
    classification = metrics.get("classification", {})
    trading = metrics.get("trading", {})
    portfolio = metrics.get("portfolio", {})
    base = portfolio.get("cost_1x", {})
    return {
        "experiment_id": experiment_id,
        "phase": phase,
        "target": target,
        "feature_set": feature_set,
        "architecture": architecture,
        "class_weight": class_weight,
        "parameters": (parameters or {}).get("name") if parameters else None,
        "seed": seed,
        "roc_auc": classification.get("roc_auc"),
        "pr_auc": classification.get("pr_auc"),
        "pr_baseline": classification.get("positive_class_rate"),
        "brier": classification.get("brier_score"),
        "trades": trading.get("trades"),
        "profit_factor": base.get("profit_factor", trading.get("profit_factor")),
        "portfolio_return": base.get("portfolio_return"),
        "max_drawdown": base.get("maximum_drawdown", trading.get("maximum_drawdown")),
        "cost_1_5x": portfolio.get("cost_1_5x", {}).get("portfolio_return"),
        "cost_2x": portfolio.get("cost_2x", {}).get("portfolio_return"),
        "score": score,
        "error": error,
    }


def _run_one(
    *,
    split: ResearchSplit,
    feature_set: FeatureSet,
    parameters: dict[str, Any],
    seed: int,
    class_weight: str,
    architecture: str,
    training: TrainingConfig,
) -> tuple[ResearchBundle, dict[str, Any], dict[str, Any]]:
    label = (
        f"model architecture={architecture} features={feature_set.name} "
        f"params={parameters.get('name', 'custom')} seed={seed} class_weight={class_weight}"
    )
    if _PROGRESS is None:
        bundle, selection = build_bundle(
            split,
            feature_set,
            parameters,
            seed,
            class_weight,
            architecture,
            training,
        )
        metrics = evaluate_bundle(bundle, split.development_oos, training)
        return bundle, selection, metrics

    with _PROGRESS.task(
        "model_experiment",
        label,
        architecture=architecture,
        feature_set=feature_set.name,
        parameters=parameters.get("name"),
        seed=seed,
        class_weight=class_weight,
    ):
        bundle, selection = build_bundle(
            split,
            feature_set,
            parameters,
            seed,
            class_weight,
            architecture,
            training,
        )
        metrics = evaluate_bundle(bundle, split.development_oos, training)
    summary = _metric_row(
        experiment_id="live",
        phase=_PROGRESS.current_phase_name,
        target="live",
        feature_set=feature_set.name,
        architecture=architecture,
        class_weight=class_weight,
        parameters=parameters,
        seed=seed,
        metrics=metrics,
        score=economic_score(metrics),
    )
    _PROGRESS.experiment_result(summary)
    return bundle, selection, metrics



def _target_diagnostics(frame: pd.DataFrame) -> dict[str, Any]:
    df = frame.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)

    def group(column: str) -> dict[str, Any]:
        if column not in df.columns:
            return {}
        rows = {}
        for value, part in df.groupby(column, dropna=False):
            rows[str(value)] = {
                "rows": int(len(part)),
                "positive_rate": float(part["target_good_trade"].mean()) if len(part) else None,
                "mean_net_return": float(part["net_return"].mean()) if len(part) else None,
                "median_net_return": float(part["net_return"].median()) if len(part) else None,
            }
        return rows

    return {
        "rows": int(len(df)),
        "positive_class_rate": float(df["target_good_trade"].mean()) if len(df) else None,
        "net_return_mean": float(df["net_return"].mean()) if len(df) else None,
        "net_return_median": float(df["net_return"].median()) if len(df) else None,
        "exit_reason": df["exit_reason"].astype(str).value_counts(dropna=False).to_dict() if "exit_reason" in df.columns else {},
        "by_month": group("month"),
        "by_symbol": group("symbol"),
        "by_strategy": group("strategy_name"),
        "by_trend_regime": group("trend_regime"),
        "by_volatility_regime": group("volatility_regime"),
    }

def _all_signal_baseline(frame: pd.DataFrame, training: TrainingConfig) -> dict[str, Any]:
    kwargs = {
        "interval": training.interval,
        "starting_capital": training.backtest_starting_capital,
        "risk_per_trade_pct": training.backtest_risk_per_trade_pct,
        "max_position_share_pct": training.backtest_max_position_share_pct,
        "max_concurrent_positions": training.backtest_max_concurrent_positions,
        "max_portfolio_risk_pct": training.backtest_max_portfolio_risk_pct,
        "max_gross_exposure_pct": training.backtest_max_gross_exposure_pct,
        "base_round_trip_cost": 2 * (training.fee + training.slippage),
        "trade_all_signals": True,
    }
    result = {"all": run_portfolio_backtest(frame, None, 0.5, **kwargs), "by_strategy": {}}
    for strategy, part in frame.groupby("strategy_name"):
        result["by_strategy"][str(strategy)] = run_portfolio_backtest(part, None, 0.5, **kwargs)
    return result


def _selected_rows(frame: pd.DataFrame, probabilities: np.ndarray, thresholds: dict[str, float]) -> pd.DataFrame:
    df = frame.copy().reset_index(drop=True)
    df["probability"] = probabilities
    threshold = np.asarray(
        [thresholds.get(str(strategy), thresholds.get("__global__", 0.5)) for strategy in df["strategy_name"]],
        dtype=float,
    )
    return df[df["probability"].to_numpy(dtype=float) >= threshold].copy()


def _concentration(frame: pd.DataFrame, probabilities: np.ndarray, thresholds: dict[str, float]) -> dict[str, Any]:
    selected = _selected_rows(frame, probabilities, thresholds)
    if selected.empty:
        return {"trades": 0, "top_symbol_share": None, "top_month_share": None, "top_strategy_trade_share": None}
    selected["timestamp"] = pd.to_datetime(selected["timestamp"])
    selected["month"] = selected["timestamp"].dt.to_period("M").astype(str)
    positive_total = float(selected.loc[selected["net_return"] > 0, "net_return"].sum())

    def pnl_share(column: str) -> float | None:
        if positive_total <= 0:
            return None
        grouped = selected.groupby(column)["net_return"].sum().clip(lower=0)
        return float(grouped.max() / positive_total) if len(grouped) else None

    strategy_share = float(selected["strategy_name"].value_counts(normalize=True).max())
    return {
        "trades": int(len(selected)),
        "top_symbol_pnl_share": pnl_share("symbol"),
        "top_month_pnl_share": pnl_share("month"),
        "top_strategy_trade_share": strategy_share,
        "by_symbol": selected.groupby("symbol")["net_return"].agg(["count", "mean", "sum"]).to_dict("index"),
        "by_month": selected.groupby("month")["net_return"].agg(["count", "mean", "sum"]).to_dict("index"),
        "by_strategy": selected.groupby("strategy_name")["net_return"].agg(["count", "mean", "sum"]).to_dict("index"),
    }



def _error_analysis(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    thresholds: dict[str, float],
    feature_set: FeatureSet,
) -> dict[str, Any]:
    df = frame.copy().reset_index(drop=True)
    df["probability"] = np.asarray(probabilities, dtype=float)
    threshold_values = np.asarray(
        [thresholds.get(str(strategy), thresholds.get("__global__", 0.5)) for strategy in df["strategy_name"]],
        dtype=float,
    )
    df["selected"] = df["probability"].to_numpy(dtype=float) >= threshold_values
    y = df["target_good_trade"].astype(int)
    false_positive = df[df["selected"] & y.eq(0)].copy()
    false_negative = df[~df["selected"] & y.eq(1)].copy()
    allowed_stop = false_positive[false_positive.get("exit_reason", pd.Series(index=false_positive.index, dtype=object)).eq("stop_loss")]

    def grouped(part: pd.DataFrame, column: str) -> dict[str, Any]:
        if column not in part.columns or part.empty:
            return {}
        values = part.groupby(column, dropna=False)["net_return"].agg(["count", "mean", "sum"])
        return {str(index): {key: float(value) if key != "count" else int(value) for key, value in row.items()} for index, row in values.to_dict("index").items()}

    numeric_features = [column for column in feature_set.columns if column not in feature_set.cat_features]
    numeric_features = [column for column in numeric_features if column in df.columns]
    def feature_means(part: pd.DataFrame) -> dict[str, float]:
        if part.empty or not numeric_features:
            return {}
        values = part[numeric_features].apply(pd.to_numeric, errors="coerce").mean().dropna()
        return {str(key): float(value) for key, value in values.items()}

    return {
        "rows": int(len(df)),
        "selected": int(df["selected"].sum()),
        "false_positive": int(len(false_positive)),
        "false_negative": int(len(false_negative)),
        "allowed_stop_loss": int(len(allowed_stop)),
        "false_positive_mean_net_return": float(false_positive["net_return"].mean()) if len(false_positive) else None,
        "false_negative_mean_net_return": float(false_negative["net_return"].mean()) if len(false_negative) else None,
        "false_positive_by_strategy": grouped(false_positive, "strategy_name"),
        "false_negative_by_strategy": grouped(false_negative, "strategy_name"),
        "false_positive_by_symbol": grouped(false_positive, "symbol"),
        "false_negative_by_symbol": grouped(false_negative, "symbol"),
        "false_positive_by_trend_regime": grouped(false_positive, "trend_regime"),
        "false_negative_by_trend_regime": grouped(false_negative, "trend_regime"),
        "false_positive_by_volatility_regime": grouped(false_positive, "volatility_regime"),
        "false_negative_by_volatility_regime": grouped(false_negative, "volatility_regime"),
        "false_positive_feature_means": feature_means(false_positive),
        "false_negative_feature_means": feature_means(false_negative),
    }


def _csv_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No successful experiments in this phase._\n"
    return "```csv\n" + frame.to_csv(index=False) + "```\n"

def _promotion_readiness(
    metrics: dict[str, Any],
    walk_forward: dict[str, Any],
    concentration: dict[str, Any],
    seed_stability: dict[str, Any],
    config: ResearchConfig,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    classification = metrics.get("classification", {})
    trading = metrics.get("trading", {})
    portfolio = metrics.get("portfolio", {})
    base = portfolio.get("cost_1x", {})
    stress15 = portfolio.get("cost_1_5x", {})
    stress20 = portfolio.get("cost_2x", {})
    roc = classification.get("roc_auc")
    pr = classification.get("pr_auc")
    baseline = classification.get("positive_class_rate")
    if roc is None or float(roc) <= 0.5:
        reasons.append("ROC AUC is not above 0.5")
    if pr is None or baseline is None or float(pr) <= float(baseline):
        reasons.append("PR AUC does not beat class baseline")
    if int(trading.get("trades") or 0) < config.minimum_final_trades:
        reasons.append("too few OOS trades")
    if float(base.get("portfolio_return") or 0.0) <= config.minimum_oos_portfolio_return:
        reasons.append("OOS portfolio return is not positive")
    pf = base.get("profit_factor")
    if pf is None or float(pf) <= config.minimum_oos_profit_factor:
        reasons.append("OOS portfolio profit factor is too low")
    if trading.get("mean_net_return") is None or float(trading.get("mean_net_return") or 0.0) <= 0:
        reasons.append("OOS mean selected-trade net return is not positive")
    if float(base.get("maximum_drawdown") or 0.0) < config.training.maximum_allowed_drawdown:
        reasons.append("OOS portfolio drawdown exceeds configured limit")
    all_signals = portfolio.get("all_signals", {})
    improves_return = float(base.get("portfolio_return") or 0.0) > float(all_signals.get("portfolio_return") or 0.0)
    improves_drawdown = float(base.get("maximum_drawdown") or 0.0) > float(all_signals.get("maximum_drawdown") or 0.0)
    base_pf = base.get("profit_factor")
    all_pf = all_signals.get("profit_factor")
    improves_pf = (
        base_pf is not None
        and all_pf is not None
        and float(base_pf) > float(all_pf)
    )
    if not (improves_return or improves_drawdown or improves_pf):
        reasons.append("ML filter does not improve the all-signals baseline on return, drawdown, or profit factor")
    if config.require_positive_cost_1_5x and float(stress15.get("portfolio_return") or 0.0) <= 0:
        reasons.append("1.5x cost stress is not positive")
    if config.prefer_nonnegative_cost_2x and float(stress20.get("portfolio_return") or 0.0) < 0:
        reasons.append("2x cost stress is negative")
    positive_rate = walk_forward.get("positive_return_fold_rate")
    if positive_rate is None or float(positive_rate) < config.minimum_positive_wf_rate:
        reasons.append("walk-forward positive fold rate is below research minimum")
    positive_seed_rate = seed_stability.get("positive_portfolio_return_rate")
    if positive_seed_rate is None or float(positive_seed_rate) < config.minimum_positive_seed_rate:
        reasons.append("candidate is not stable across research seeds")
    symbol_share = concentration.get("top_symbol_pnl_share")
    if symbol_share is not None and float(symbol_share) > config.maximum_symbol_pnl_share:
        reasons.append("positive PnL is concentrated in one symbol")
    month_share = concentration.get("top_month_pnl_share")
    if month_share is not None and float(month_share) > config.maximum_month_pnl_share:
        reasons.append("positive PnL is concentrated in one month")
    if float(concentration.get("top_strategy_trade_share") or 0.0) > 0.90:
        reasons.append("selected trades are concentrated in one strategy")
    return not reasons, reasons


def _walk_forward(
    development: pd.DataFrame,
    *,
    feature_set: FeatureSet,
    parameters: dict[str, Any],
    seed: int,
    class_weight: str,
    architecture: str,
    training: TrainingConfig,
    folds: int,
) -> dict[str, Any]:
    purge = physical_purge(training.target_horizon_minutes, training.embargo_minutes)
    raw_folds = walk_forward_time_splits(
        development,
        folds=folds,
        minimum_fold_rows=max(50, min(training.minimum_fold_rows, len(development) // 20)),
        purge_timedelta=purge,
    )
    rows: list[dict[str, Any]] = []
    for index, (train, validation, test) in enumerate(raw_folds):
        try:
            fold_split = split_walk_forward_fold(train, validation, test, purge=purge)
            bundle, _, metrics = _run_one(
                split=fold_split,
                feature_set=feature_set,
                parameters=parameters,
                seed=seed,
                class_weight=class_weight,
                architecture=architecture,
                training=training,
            )
            rows.append({
                "fold": index,
                "train_start": str(train["timestamp"].min()),
                "train_end": str(train["timestamp"].max()),
                "test_start": str(test["timestamp"].min()),
                "test_end": str(test["timestamp"].max()),
                "thresholds": bundle.thresholds,
                "metrics": metrics,
            })
        except Exception as error:
            rows.append({"fold": index, "error": str(error)})
    valid = [item for item in rows if "metrics" in item]
    returns = [float(item["metrics"]["portfolio"]["cost_1x"].get("portfolio_return") or 0.0) for item in valid]
    return {
        "folds": rows,
        "completed_folds": len(valid),
        "positive_return_fold_rate": float(np.mean(np.asarray(returns) > 0)) if returns else None,
        "median_portfolio_return": float(np.median(returns)) if returns else None,
        "worst_portfolio_return": float(np.min(returns)) if returns else None,
    }


def run_research(config: ResearchConfig, *, update_data: bool) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    training = config.training
    output = config.output_root
    output.mkdir(parents=True, exist_ok=True)
    reports_dir = output / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    git_sha = _git_sha()
    progress = ResearchProgress(output)
    global _PROGRESS
    _PROGRESS = progress
    progress.emit(
        "start",
        f"mode={config.mode}; update_history={update_data}; output={output}",
        phase="startup",
        git_sha=git_sha,
    )
    progress.phase(1, 9, "data", "update/load/audit Binance history")

    if update_data:
        update_report = update_history(training)
    else:
        update_report = {"status": "skipped_by_flag"}
    if not training.history_path.exists():
        raise FileNotFoundError(
            f"history dataset not found: {training.history_path}. Run with --update-history or mount the project training/data directory."
        )
    if training.history_path.suffix.lower() == ".csv":
        history = pd.read_csv(training.history_path)
    else:
        history = pd.read_parquet(training.history_path)
    history_hash = sha256_file(training.history_path)
    data_audit = audit_history(history, interval=training.interval, expected_symbols=training.symbols)
    atomic_json(reports_dir / "DATA_AUDIT.json", {"update": update_report, "history_hash": history_hash, "audit": data_audit})
    if not data_audit["pass"]:
        raise ValueError("history audit failed; research is blocked")

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_ref": SOURCE_REF,
        "git_sha": git_sha,
        "history_sha256": history_hash,
        "history_period": f"{data_audit['start']} → {data_audit['end']}",
        "mode": config.mode,
    }

    progress.emit(
        "result",
        f"history rows={len(history)} period={data_audit['start']} -> {data_audit['end']} hash={history_hash[:12]}...",
        phase="data",
        rows=len(history),
        history_start=data_audit["start"],
        history_end=data_audit["end"],
    )
    progress.phase(2, 9, "target", f"target search: {len(config.target_experiments)} target configurations")

    experiment_rows: list[dict[str, Any]] = []
    experiment_details: list[dict[str, Any]] = []
    target_results: list[dict[str, Any]] = []
    fixed_params = config.model_parameter_space[0]
    base_features = feature_sets(include_market_context=False)[0]

    # Phase C: target research uses only development data. Final holdout is untouched.
    target_datasets: dict[str, pd.DataFrame] = {}
    target_splits: dict[str, ResearchSplit] = {}
    target_training: dict[str, TrainingConfig] = {}
    target_hashes: dict[str, str] = {}
    target_diagnostics: dict[str, dict[str, Any]] = {}
    for target in config.target_experiments:
        target_cfg = target.apply(training)
        try:
            dataset = build_dataset(config=target_cfg, raw_df=history, save=False)
            dataset = drop_incomplete(dataset, base_features)
            split = split_research_dataset(
                dataset,
                final_holdout_days=config.final_holdout_days,
                purge=physical_purge(target_cfg.target_horizon_minutes, target_cfg.embargo_minutes),
            )
            if len(split.train) < config.development_min_rows:
                raise ValueError(f"target development train too small: {len(split.train)}")
            target_datasets[target.name] = dataset
            target_splits[target.name] = split
            target_training[target.name] = target_cfg
            target_hashes[target.name] = dataframe_sha256(dataset)
            target_diagnostics[target.name] = _target_diagnostics(dataset)
            candidates = []
            for weight_mode in ("none", "balanced"):
                try:
                    bundle, selection, metrics = _run_one(
                        split=split,
                        feature_set=base_features,
                        parameters=fixed_params,
                        seed=42,
                        class_weight=weight_mode,
                        architecture="pooled",
                        training=target_cfg,
                    )
                    score = economic_score(metrics)
                    row = _metric_row(
                        experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="target", target=target.name,
                        feature_set=base_features.name, architecture="pooled", class_weight=weight_mode,
                        parameters=fixed_params, seed=42, metrics=metrics, score=score,
                    )
                    experiment_rows.append(row)
                    detail = {"row": row, "bundle": bundle, "selection": selection, "metrics": metrics}
                    experiment_details.append(detail)
                    candidates.append(detail)
                except Exception as error:
                    row = _metric_row(
                        experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="target", target=target.name,
                        feature_set=base_features.name, architecture="pooled", class_weight=weight_mode,
                        parameters=fixed_params, seed=42, metrics=None, score=None, error=str(error),
                    )
                    experiment_rows.append(row)
            if candidates:
                best = max(candidates, key=lambda item: float(item["row"]["score"]))
                target_results.append({"target": target, "best": best})
        except Exception as error:
            experiment_rows.append(_metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="target", target=target.name,
                feature_set=base_features.name, architecture="pooled", class_weight="n/a", parameters=fixed_params,
                seed=42, metrics=None, score=None, error=str(error),
            ))
    if not target_results:
        raise RuntimeError("no target experiment completed successfully")
    selected_target_result = max(target_results, key=lambda item: float(item["best"]["row"]["score"]))
    selected_target: TargetExperiment = selected_target_result["target"]
    selected_target_name = selected_target.name
    selected_training = target_training[selected_target_name]
    selected_dataset = target_datasets[selected_target_name]
    selected_split = target_splits[selected_target_name]
    initial_weight = selected_target_result["best"]["row"]["class_weight"]
    progress.emit(
        "selected",
        f"target={selected_target_name}; initial_class_weight={initial_weight}",
        phase="target",
        target=selected_target_name,
        class_weight=initial_weight,
    )
    atomic_json(reports_dir / "TARGET_DIAGNOSTICS.json", target_diagnostics)

    progress.phase(3, 9, "baselines", "base signals + logistic/constant baseline + regression target")

    base_signal = _all_signal_baseline(selected_split.development_oos, selected_training)
    # Constant and logistic baselines use train -> threshold-selection -> development OOS.
    # The final holdout remains untouched.
    try:
        base_signal["model_baselines"] = _baseline_reports(
            selected_split.train,
            selected_split.threshold_selection,
            selected_split.development_oos,
            selected_training,
        )
    except Exception as error:
        base_signal["model_baselines"] = {"error": str(error)}
    atomic_json(reports_dir / "BASE_SIGNAL_REPORT.json", base_signal)

    # Target C: research-only regression of realized net utility.  This does not
    # change the classifier deployment contract; it is an explicit alternative
    # hypothesis compared on development OOS only.
    regression_result: dict[str, Any] = {"status": "not_run"}
    try:
        regression_bundle, regression_selection = fit_regression_bundle(
            selected_split, base_features, fixed_params, 42, selected_training
        )
        regression_metrics = evaluate_regression_bundle(
            regression_bundle, selected_split.development_oos, selected_training
        )
        regression_score = regression_economic_score(regression_metrics)
        regression_row = _metric_row(
            experiment_id=f"exp_{len(experiment_rows)+1:04d}",
            phase="regression_target",
            target="future_net_return_regression",
            feature_set=base_features.name,
            architecture="catboost_regressor",
            class_weight="n/a",
            parameters=fixed_params,
            seed=42,
            metrics=regression_metrics,
            score=regression_score,
        )
        experiment_rows.append(regression_row)
        regression_result = {
            "status": "completed",
            "selection": regression_selection,
            "metrics": regression_metrics,
            "score": regression_score,
        }
    except Exception as error:
        regression_result = {"status": "failed", "error": str(error)}
        experiment_rows.append(_metric_row(
            experiment_id=f"exp_{len(experiment_rows)+1:04d}",
            phase="regression_target",
            target="future_net_return_regression",
            feature_set=base_features.name,
            architecture="catboost_regressor",
            class_weight="n/a",
            parameters=fixed_params,
            seed=42,
            metrics=None,
            score=None,
            error=str(error),
        ))
    atomic_json(reports_dir / "REGRESSION_TARGET.json", regression_result)

    progress.phase(4, 9, "features", "feature ablation + BTC/market context")

    # Phase D: feature ablations and research-only market context.
    augmented = None
    try:
        augmented = augment_market_context(selected_dataset, history)
    except Exception as error:
        atomic_json(reports_dir / "MARKET_CONTEXT_ERROR.json", {"error": str(error)})
    feature_results: list[dict[str, Any]] = []
    available_sets = feature_sets(include_market_context=augmented is not None)
    if config.mode == "quick":
        available_sets = [item for item in available_sets if item.name in {"production_full", "minus_identity", "minus_volume", "production_plus_btc"}]
    for fset in available_sets:
        source = augmented if (augmented is not None and not fset.production_compatible) else selected_dataset
        try:
            cleaned = drop_incomplete(source, fset)
            split = split_research_dataset(cleaned, final_holdout_days=config.final_holdout_days, purge=physical_purge(selected_training.target_horizon_minutes, selected_training.embargo_minutes))
            bundle, selection, metrics = _run_one(
                split=split, feature_set=fset, parameters=fixed_params, seed=42,
                class_weight=initial_weight, architecture="pooled", training=selected_training,
            )
            score = economic_score(metrics)
            row = _metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="feature", target=selected_target_name,
                feature_set=fset.name, architecture="pooled", class_weight=initial_weight,
                parameters=fixed_params, seed=42, metrics=metrics, score=score,
            )
            experiment_rows.append(row)
            feature_results.append({"row": row, "bundle": bundle, "selection": selection, "metrics": metrics, "split": split, "dataset": cleaned, "feature_set": fset})
        except Exception as error:
            experiment_rows.append(_metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="feature", target=selected_target_name,
                feature_set=fset.name, architecture="pooled", class_weight=initial_weight,
                parameters=fixed_params, seed=42, metrics=None, score=None, error=str(error),
            ))
    if not feature_results:
        raise RuntimeError("no feature experiment completed successfully")
    best_research_feature = max(feature_results, key=lambda item: float(item["row"]["score"]))
    deployable_features = [item for item in feature_results if item["feature_set"].production_compatible]
    if not deployable_features:
        raise RuntimeError("no production-compatible feature experiment succeeded")
    best_deployable_feature = max(deployable_features, key=lambda item: float(item["row"]["score"]))
    chosen_feature: FeatureSet = best_deployable_feature["feature_set"]
    chosen_dataset = best_deployable_feature["dataset"]
    chosen_split = best_deployable_feature["split"]
    progress.emit(
        "selected",
        f"deployable_feature_set={chosen_feature.name}; research_best={best_research_feature['feature_set'].name}",
        phase="features",
        deployable_feature_set=chosen_feature.name,
        research_best_feature_set=best_research_feature["feature_set"].name,
    )

    progress.phase(5, 9, "architecture", "architecture comparison + class-weight search")

    # Phase E: pooled vs strategy/symbol-specific models. Separate models are
    # research-only with the current single-model online contract.
    architecture_results: list[dict[str, Any]] = []
    architectures = ("pooled", "separate_strategy", "separate_symbol")
    for architecture in architectures:
        try:
            bundle, selection, metrics = _run_one(
                split=chosen_split, feature_set=chosen_feature, parameters=fixed_params, seed=42,
                class_weight=initial_weight, architecture=architecture, training=selected_training,
            )
            score = economic_score(metrics)
            row = _metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="architecture", target=selected_target_name,
                feature_set=chosen_feature.name, architecture=architecture, class_weight=initial_weight,
                parameters=fixed_params, seed=42, metrics=metrics, score=score,
            )
            experiment_rows.append(row)
            architecture_results.append({"row": row, "bundle": bundle, "selection": selection, "metrics": metrics})
        except Exception as error:
            experiment_rows.append(_metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="architecture", target=selected_target_name,
                feature_set=chosen_feature.name, architecture=architecture, class_weight=initial_weight,
                parameters=fixed_params, seed=42, metrics=None, score=None, error=str(error),
            ))
    if augmented is not None:
        liquidity_set = next((item for item in feature_sets(include_market_context=True) if item.name == "production_plus_market_context"), None)
        if liquidity_set is not None:
            try:
                liquidity_data = drop_incomplete(augmented, liquidity_set)
                liquidity_split = split_research_dataset(
                    liquidity_data,
                    final_holdout_days=config.final_holdout_days,
                    purge=physical_purge(selected_training.target_horizon_minutes, selected_training.embargo_minutes),
                )
                bundle, selection, metrics = _run_one(
                    split=liquidity_split, feature_set=liquidity_set, parameters=fixed_params, seed=42,
                    class_weight=initial_weight, architecture="separate_liquidity", training=selected_training,
                )
                score = economic_score(metrics)
                row = _metric_row(
                    experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="architecture", target=selected_target_name,
                    feature_set=liquidity_set.name, architecture="separate_liquidity", class_weight=initial_weight,
                    parameters=fixed_params, seed=42, metrics=metrics, score=score,
                )
                experiment_rows.append(row)
                architecture_results.append({"row": row, "bundle": bundle, "selection": selection, "metrics": metrics})
            except Exception as error:
                experiment_rows.append(_metric_row(
                    experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="architecture", target=selected_target_name,
                    feature_set="production_plus_market_context", architecture="separate_liquidity", class_weight=initial_weight,
                    parameters=fixed_params, seed=42, metrics=None, score=None, error=str(error),
                ))

    best_architecture = max(architecture_results, key=lambda item: float(item["row"]["score"])) if architecture_results else None
    # Deployment remains pooled until online multi-model routing is explicitly implemented and validated.
    deploy_architecture = "pooled"

    # Class-imbalance experiment.
    weight_results: list[dict[str, Any]] = []
    for mode in ("none", "balanced", "positive_x2.0"):
        try:
            bundle, selection, metrics = _run_one(
                split=chosen_split, feature_set=chosen_feature, parameters=fixed_params, seed=42,
                class_weight=mode, architecture=deploy_architecture, training=selected_training,
            )
            score = economic_score(metrics)
            row = _metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="class_weight", target=selected_target_name,
                feature_set=chosen_feature.name, architecture=deploy_architecture, class_weight=mode,
                parameters=fixed_params, seed=42, metrics=metrics, score=score,
            )
            experiment_rows.append(row)
            weight_results.append({"row": row, "bundle": bundle, "selection": selection, "metrics": metrics})
        except Exception as error:
            experiment_rows.append(_metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="class_weight", target=selected_target_name,
                feature_set=chosen_feature.name, architecture=deploy_architecture, class_weight=mode,
                parameters=fixed_params, seed=42, metrics=None, score=None, error=str(error),
            ))
    if not weight_results:
        raise RuntimeError("no class-weight experiment succeeded")
    selected_weight = max(weight_results, key=lambda item: float(item["row"]["score"]))["row"]["class_weight"]
    progress.emit(
        "selected",
        f"deploy_architecture={deploy_architecture}; class_weight={selected_weight}",
        phase="architecture",
        architecture=deploy_architecture,
        class_weight=selected_weight,
    )

    progress.phase(6, 9, "tuning", f"CatBoost tuning: {len(config.model_parameter_space)} parameter sets x {len(config.model_seeds[: (2 if config.mode == 'quick' else 3)])} seeds")

    # Phase F: tune a compact CatBoost search. Rank parameter sets by median score across seeds.
    tuning_rows: list[dict[str, Any]] = []
    seeds_for_tuning = config.model_seeds[: (2 if config.mode == "quick" else 3)]
    for parameters in config.model_parameter_space:
        for seed in seeds_for_tuning:
            try:
                bundle, selection, metrics = _run_one(
                    split=chosen_split, feature_set=chosen_feature, parameters=parameters, seed=seed,
                    class_weight=selected_weight, architecture=deploy_architecture, training=selected_training,
                )
                score = economic_score(metrics)
                row = _metric_row(
                    experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="tuning", target=selected_target_name,
                    feature_set=chosen_feature.name, architecture=deploy_architecture, class_weight=selected_weight,
                    parameters=parameters, seed=seed, metrics=metrics, score=score,
                )
                experiment_rows.append(row)
                tuning_rows.append({"row": row, "bundle": bundle, "selection": selection, "metrics": metrics, "parameters": parameters})
            except Exception as error:
                experiment_rows.append(_metric_row(
                    experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="tuning", target=selected_target_name,
                    feature_set=chosen_feature.name, architecture=deploy_architecture, class_weight=selected_weight,
                    parameters=parameters, seed=seed, metrics=None, score=None, error=str(error),
                ))
    if not tuning_rows:
        raise RuntimeError("no CatBoost tuning experiment succeeded")
    by_param: dict[str, list[float]] = {}
    param_lookup: dict[str, dict[str, Any]] = {}
    for item in tuning_rows:
        name = str(item["parameters"]["name"])
        by_param.setdefault(name, []).append(float(item["row"]["score"]))
        param_lookup[name] = item["parameters"]
    selected_param_name = max(by_param, key=lambda name: median(by_param[name]))
    selected_parameters = param_lookup[selected_param_name]
    progress.emit(
        "selected",
        f"CatBoost parameters={selected_param_name}",
        phase="tuning",
        parameters=selected_param_name,
    )

    progress.phase(7, 9, "seed_stability", f"seed stability: {len(config.model_seeds)} seeds")

    # Seed stability: do not choose the luckiest seed. Use the median-scoring seed.
    seed_results: list[dict[str, Any]] = []
    for seed in config.model_seeds:
        try:
            bundle, selection, metrics = _run_one(
                split=chosen_split, feature_set=chosen_feature, parameters=selected_parameters, seed=seed,
                class_weight=selected_weight, architecture=deploy_architecture, training=selected_training,
            )
            score = economic_score(metrics)
            row = _metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="seed_stability", target=selected_target_name,
                feature_set=chosen_feature.name, architecture=deploy_architecture, class_weight=selected_weight,
                parameters=selected_parameters, seed=seed, metrics=metrics, score=score,
            )
            experiment_rows.append(row)
            seed_results.append({"row": row, "bundle": bundle, "selection": selection, "metrics": metrics})
        except Exception as error:
            experiment_rows.append(_metric_row(
                experiment_id=f"exp_{len(experiment_rows)+1:04d}", phase="seed_stability", target=selected_target_name,
                feature_set=chosen_feature.name, architecture=deploy_architecture, class_weight=selected_weight,
                parameters=selected_parameters, seed=seed, metrics=None, score=None, error=str(error),
            ))
    if not seed_results:
        raise RuntimeError("seed stability failed for every seed")
    ordered_seeds = sorted(seed_results, key=lambda item: float(item["row"]["score"]))
    selected_seed_result = ordered_seeds[len(ordered_seeds) // 2]
    selected_seed = int(selected_seed_result["row"]["seed"])
    seed_returns = [float(item["metrics"]["portfolio"]["cost_1x"].get("portfolio_return") or 0.0) for item in seed_results]
    seed_scores = [float(item["row"]["score"]) for item in seed_results]
    seed_stability = {
        "seeds": [int(item["row"]["seed"]) for item in seed_results],
        "portfolio_returns": seed_returns,
        "scores": seed_scores,
        "positive_portfolio_return_rate": float(np.mean(np.asarray(seed_returns) > 0)) if seed_returns else None,
        "median_portfolio_return": float(np.median(seed_returns)) if seed_returns else None,
        "worst_portfolio_return": float(np.min(seed_returns)) if seed_returns else None,
        "score_std": float(np.std(seed_scores)) if seed_scores else None,
        "selected_median_seed": selected_seed,
    }
    atomic_json(output / "SEED_STABILITY.json", seed_stability)
    progress.emit(
        "selected",
        f"median seed={selected_seed}; development decisions are now frozen",
        phase="seed_stability",
        selected_seed=selected_seed,
    )

    progress.phase(8, 9, "final_validation", "untouched final holdout + walk-forward + block bootstrap + promotion gates")

    # Freeze all research decisions before touching the final holdout.
    evaluation_bundle, selection_report = build_bundle(
        chosen_split,
        chosen_feature,
        selected_parameters,
        selected_seed,
        selected_weight,
        deploy_architecture,
        selected_training,
    )
    holdout = chosen_split.final_holdout
    final_metrics = evaluate_bundle(evaluation_bundle, holdout, selected_training)
    holdout_probabilities = predict_bundle(evaluation_bundle, holdout)
    concentration = _concentration(holdout, holdout_probabilities, evaluation_bundle.thresholds)
    error_analysis = _error_analysis(holdout, holdout_probabilities, evaluation_bundle.thresholds, chosen_feature)

    holdout_start = pd.Timestamp(chosen_split.metadata["holdout_start"])
    development = chosen_dataset[pd.to_datetime(chosen_dataset["timestamp"]) < holdout_start - physical_purge(selected_training.target_horizon_minutes, selected_training.embargo_minutes)].copy()
    walk_forward = _walk_forward(
        development,
        feature_set=chosen_feature,
        parameters=selected_parameters,
        seed=selected_seed,
        class_weight=selected_weight,
        architecture=deploy_architecture,
        training=selected_training,
        folds=selected_training.walk_forward_folds,
    )
    confidence = block_bootstrap_report(
        holdout,
        holdout_probabilities,
        evaluation_bundle.thresholds,
        interval=selected_training.interval,
        base_round_trip_cost=2 * (selected_training.fee + selected_training.slippage),
        iterations=selected_training.bootstrap_iterations,
        block_size=selected_training.bootstrap_block_size,
        random_seed=selected_seed,
        backtest_kwargs={
            "starting_capital": selected_training.backtest_starting_capital,
            "risk_per_trade_pct": selected_training.backtest_risk_per_trade_pct,
            "max_position_share_pct": selected_training.backtest_max_position_share_pct,
            "max_concurrent_positions": selected_training.backtest_max_concurrent_positions,
            "max_portfolio_risk_pct": selected_training.backtest_max_portfolio_risk_pct,
            "max_gross_exposure_pct": selected_training.backtest_max_gross_exposure_pct,
        },
    )
    final_metrics["confidence_intervals"] = confidence
    promotion_ready, promotion_reasons = _promotion_readiness(
        final_metrics, walk_forward, concentration, seed_stability, config
    )
    progress.emit(
        "result",
        f"final gates: promotion_ready={promotion_ready}; reasons={len(promotion_reasons)}",
        phase="final_validation",
        promotion_ready=promotion_ready,
        promotion_reasons=promotion_reasons,
    )

    progress.phase(9, 9, "finalize", "candidate export (only if gated) + reports + experiment artifacts")

    research_config_payload = {
        "target": selected_target.to_dict(),
        "feature_set": chosen_feature.name,
        "feature_columns": list(chosen_feature.columns),
        "architecture": deploy_architecture,
        "best_research_feature_set": best_research_feature["feature_set"].name,
        "best_research_architecture": best_architecture["row"]["architecture"] if best_architecture else None,
        "class_weight": selected_weight,
        "parameters": selected_parameters,
        "seed": selected_seed,
        "thresholds": evaluation_bundle.thresholds,
        "calibration": evaluation_bundle.calibration_methods,
        "train_start": str(chosen_split.train["timestamp"].min()),
        "evaluation_train_end": str(chosen_split.train["timestamp"].max()),
        "final_holdout_start": str(holdout["timestamp"].min()),
        "final_holdout_end": str(holdout["timestamp"].max()),
        "promotion_ready": promotion_ready,
        "promotion_reasons": promotion_reasons,
    }
    atomic_json(output / "BEST_RESEARCH_CONFIG.json", research_config_payload)
    atomic_json(output / "FINAL_METRICS.json", final_metrics)
    atomic_json(output / "WALK_FORWARD.json", walk_forward)
    atomic_json(output / "CONCENTRATION.json", concentration)
    atomic_json(output / "ERROR_ANALYSIS.json", error_analysis)

    candidate_export = None
    production_refit = None
    explanations: dict[str, Any] = {
        "status": "not_run",
        "reason": "candidate did not pass all economic/robustness gates",
    }
    if promotion_ready and chosen_feature.production_compatible and deploy_architecture == "pooled":
        # The exact OOS evaluation model is frozen above.  Only after it passes
        # the gates do we fit a later deployable bundle.  No OOS metrics are
        # claimed for the refitted artifact itself.
        deployment_split = split_deployment_dataset(
            chosen_dataset,
            purge=physical_purge(selected_training.target_horizon_minutes, selected_training.embargo_minutes),
        )
        deployable_bundle, deployment_selection = build_bundle(
            deployment_split,
            chosen_feature,
            selected_parameters,
            selected_seed,
            selected_weight,
            deploy_architecture,
            selected_training,
        )
        production_refit = {
            "split": deployment_split.metadata,
            "selection": deployment_selection,
            "train_start": str(deployment_split.train["timestamp"].min()),
            "train_end": str(deployment_split.train["timestamp"].max()),
            "metrics": "NOT OOS — exact deployable refit is not assigned evaluation metrics",
        }
        research_config_payload["production_train_start"] = production_refit["train_start"]
        research_config_payload["production_train_end"] = production_refit["train_end"]
        atomic_json(output / "BEST_RESEARCH_CONFIG.json", research_config_payload)
        explanations = explain_pooled_bundle(evaluation_bundle, holdout)
        atomic_json(output / "MODEL_EXPLANATIONS.json", explanations)
        candidate_export = export_research_candidate(
            bundle=deployable_bundle,
            final_frame=holdout,
            final_metrics=final_metrics,
            walk_forward=walk_forward,
            deployment_frame=chosen_dataset,
            research_config=research_config_payload,
            training=selected_training,
            dataset_report=chosen_dataset.attrs.get("dataset_report", {}),
        )
        atomic_json(output / "PRODUCTION_REFIT.json", production_refit)
        atomic_json(output / "BEST_RESEARCH_CANDIDATE.json", candidate_export)

    experiments_dir = output / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)
    target_lookup = {item.name: item.to_dict() for item in config.target_experiments}
    for row in experiment_rows:
        row["git_sha"] = git_sha
        row["history_sha256"] = history_hash
        row["history_max_timestamp"] = data_audit["end"]
        row["dataset_hash"] = target_hashes.get(str(row.get("target")))
        split = target_splits.get(str(row.get("target")))
        payload = {
            **row,
            "target_config": target_lookup.get(str(row.get("target"))),
            "feature_groups": [row.get("feature_set")],
            "model_config": {
                "architecture": row.get("architecture"),
                "class_weight": row.get("class_weight"),
                "parameters": row.get("parameters"),
                "seed": row.get("seed"),
            },
            "periods": split.metadata if split is not None else None,
        }
        atomic_json(experiments_dir / f"{row['experiment_id']}.json", payload)

    table = experiment_table(experiment_rows)
    table.to_csv(output / "EXPERIMENT_TABLE.csv", index=False)

    # Requested reports. These are generated from the same frozen run state.
    failure = final_metrics.get("probability_rank_diagnostics", {})
    atomic_text(reports_dir / "ML_FAILURE_ANALYSIS.md", header("ML Failure Analysis", meta) + "\n" + json.dumps(failure, ensure_ascii=False, indent=2, default=str) + "\n")
    atomic_text(reports_dir / "BASE_SIGNAL_REPORT.md", header("Base Signal Report", meta) + "\n" + json.dumps(base_signal, ensure_ascii=False, indent=2, default=str) + "\n")
    target_table = table[table["phase"] == "target"]
    atomic_text(reports_dir / "TARGET_EXPERIMENT_REPORT.md", header("Target Experiment Report", meta) + f"\nSelected target: **{selected_target_name}**\n\n" + _csv_markdown(target_table) + "\n```json\n" + json.dumps(target_diagnostics, ensure_ascii=False, indent=2, default=str) + "\n```\n")
    feature_table = table[table["phase"] == "feature"]
    atomic_text(reports_dir / "FEATURE_ABLATION_REPORT.md", header("Feature Ablation Report", meta) + f"\nDeployable feature set: **{chosen_feature.name}**\n\nResearch-only best: **{best_research_feature['feature_set'].name}**\n\n" + _csv_markdown(feature_table) + "\n")
    architecture_table = table[table["phase"].isin(["architecture", "regression_target"])]
    atomic_text(reports_dir / "MODEL_ARCHITECTURE_COMPARISON.md", header("Model Architecture Comparison", meta) + "\nRegression is research-only and is not automatically deployable through the classifier gRPC contract.\n\n" + _csv_markdown(architecture_table) + "\n")
    atomic_text(reports_dir / "CALIBRATION_REPORT.md", header("Calibration Report", meta) + "\n" + json.dumps(selection_report.get("calibration", {}), ensure_ascii=False, indent=2, default=str) + "\n")
    atomic_text(reports_dir / "THRESHOLD_REPORT.md", header("Threshold Report", meta) + "\n" + json.dumps(selection_report.get("threshold_selection", {}), ensure_ascii=False, indent=2, default=str) + "\n")
    atomic_text(reports_dir / "WALK_FORWARD_REPORT.md", header("Walk Forward Report", meta) + "\n" + json.dumps(walk_forward, ensure_ascii=False, indent=2, default=str) + "\n")
    atomic_text(reports_dir / "BACKTEST_REPORT.md", header("Backtest Report", meta) + "\n" + json.dumps(final_metrics.get("portfolio", {}), ensure_ascii=False, indent=2, default=str) + "\n")
    atomic_text(reports_dir / "COST_STRESS_REPORT.md", header("Cost Stress Report", meta) + "\n" + json.dumps({k: v for k, v in final_metrics.get("portfolio", {}).items() if k.startswith("cost_")}, ensure_ascii=False, indent=2, default=str) + "\n")
    atomic_text(reports_dir / "REGIME_ROBUSTNESS_REPORT.md", header("Regime Robustness Report", meta) + "\n" + json.dumps({"trading": final_metrics.get("trading", {}), "concentration": concentration}, ensure_ascii=False, indent=2, default=str) + "\n")
    atomic_text(reports_dir / "ERROR_ANALYSIS.md", header("Error Analysis", meta) + "\n" + json.dumps({"rank_diagnostics": failure, "confusion": final_metrics.get("classification", {}).get("confusion_matrix"), "false_positive_false_negative": error_analysis}, ensure_ascii=False, indent=2, default=str) + "\n")
    sensitivity_text = "Candidate not exported; sensitivity is generated only for a promotion-ready production-compatible candidate."
    if candidate_export:
        sensitivity_text = json.dumps({"sensitivity": candidate_export.get("sensitivity", {}), "model_explanations": explanations}, ensure_ascii=False, indent=2, default=str)
    atomic_text(reports_dir / "SENSITIVITY_REPORT.md", header("Sensitivity Report", meta) + "\n" + sensitivity_text + "\n")
    final_summary = {
        "best_target": selected_target.to_dict(),
        "best_feature_set": chosen_feature.name,
        "best_research_feature_set": best_research_feature["feature_set"].name,
        "best_architecture_research": best_architecture["row"]["architecture"] if best_architecture else None,
        "regression_research": regression_result,
        "deployable_architecture": deploy_architecture,
        "selected_weight": selected_weight,
        "selected_parameters": selected_parameters,
        "selected_seed": selected_seed,
        "final_metrics": final_metrics,
        "walk_forward": walk_forward,
        "seed_stability": seed_stability,
        "concentration": concentration,
        "promotion_ready": promotion_ready,
        "promotion_reasons": promotion_reasons,
        "research_result": "BEST_RESEARCH_CANDIDATE" if promotion_ready else "NO ROBUST EDGE FOUND",
        "candidate": candidate_export,
        "production_refit": production_refit,
        "model_explanations": explanations,
        "error_analysis": error_analysis,
        "production_trading_ready": False,
    }
    atomic_text(reports_dir / "FINAL_MODEL_REPORT.md", header("Final Model Report", meta) + "\n```json\n" + json.dumps(final_summary, ensure_ascii=False, indent=2, default=str) + "\n```\n")

    result = {
        "status": "completed",
        "started_at": started.isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "meta": meta,
        "data_audit": data_audit,
        "selected": research_config_payload,
        "final_metrics": final_metrics,
        "walk_forward": walk_forward,
        "seed_stability": seed_stability,
        "concentration": concentration,
        "promotion_ready": promotion_ready,
        "promotion_reasons": promotion_reasons,
        "research_result": "BEST_RESEARCH_CANDIDATE" if promotion_ready else "NO ROBUST EDGE FOUND",
        "candidate": candidate_export,
        "production_refit": production_refit,
        "model_explanations": explanations,
        "error_analysis": error_analysis,
        "production_trading_ready": False,
        "experiment_count": len(experiment_rows),
    }
    atomic_json(output / "LATEST.json", result)
    progress.finish(
        research_result=result["research_result"],
        experiment_count=result["experiment_count"],
        promotion_ready=result["promotion_ready"],
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Leakage-safe quant research pipeline")
    parser.add_argument("--mode", choices=["quick", "full"], default="full")
    parser.add_argument("--update-history", action="store_true", help="update Binance history before research")
    parser.add_argument("--history-path", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()

    training = TrainingConfig.from_env()
    training.deploy_after_training = False
    training.candidate_only = True
    training.allow_schema_migration = False
    if args.history_path:
        training.history_path = args.history_path.expanduser().resolve()
    research = ResearchConfig(training=training, mode=args.mode)
    if args.output_root:
        research.output_root = args.output_root.expanduser().resolve()
    result = run_research(research, update_data=args.update_history)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

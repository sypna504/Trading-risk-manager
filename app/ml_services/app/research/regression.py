from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ..backtesting.simulator import run_portfolio_backtest
from ..training.training_config import TrainingConfig
from .features import FeatureSet
from .splits import ResearchSplit


@dataclass(slots=True)
class RegressionResearchBundle:
    model: CatBoostRegressor
    feature_set: FeatureSet
    threshold: float
    parameters: dict[str, Any]
    seed: int


def _pool(frame: pd.DataFrame, feature_set: FeatureSet, *, label: bool) -> Pool:
    data = frame[list(feature_set.columns)].copy()
    for column in feature_set.cat_features:
        data[column] = data[column].astype(str)
    return Pool(
        data=data,
        label=frame["net_return"] if label else None,
        cat_features=list(feature_set.cat_features),
    )


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


def fit_regression_bundle(
    split: ResearchSplit,
    feature_set: FeatureSet,
    parameters: dict[str, Any],
    seed: int,
    training: TrainingConfig,
) -> tuple[RegressionResearchBundle, dict[str, Any]]:
    params = {key: value for key, value in parameters.items() if key != "name"}
    model = CatBoostRegressor(
        **params,
        random_seed=seed,
        loss_function="RMSE",
        eval_metric="RMSE",
        verbose=False,
        allow_writing_files=False,
    )
    model.fit(
        _pool(split.train, feature_set, label=True),
        eval_set=_pool(split.model_selection, feature_set, label=True),
        early_stopping_rounds=training.early_stopping_rounds,
        use_best_model=True,
    )
    threshold_prediction = np.asarray(
        model.predict(_pool(split.threshold_selection, feature_set, label=False)), dtype=float
    )
    if not np.isfinite(threshold_prediction).all():
        raise ValueError("regression model returned non-finite predictions")
    # Candidate thresholds are based only on the threshold-selection block.
    quantiles = np.unique(np.quantile(threshold_prediction, np.linspace(0.40, 0.95, 12)))
    candidates: list[dict[str, Any]] = []
    for threshold in quantiles:
        portfolio = run_portfolio_backtest(
            split.threshold_selection,
            threshold_prediction,
            float(threshold),
            **_backtest_kwargs(training),
        )
        if int(portfolio.get("trades") or 0) < min(training.minimum_selected_trades, 20):
            continue
        score = (
            6.0 * float(portfolio.get("portfolio_return") or 0.0)
            + 0.25 * min(float(portfolio.get("profit_factor") or 0.0) - 1.0, 2.0)
            - 1.5 * abs(min(float(portfolio.get("maximum_drawdown") or 0.0), 0.0))
        )
        candidates.append({"threshold": float(threshold), "score": float(score), "portfolio": portfolio})
    if candidates:
        best = max(candidates, key=lambda item: item["score"])
        threshold = float(best["threshold"])
    else:
        threshold = float(np.median(threshold_prediction))
        best = {"threshold": threshold, "score": None, "reason": "no threshold met minimum trade count"}
    return RegressionResearchBundle(model, feature_set, threshold, parameters, seed), {
        "threshold_selection": best,
        "candidates": candidates,
    }


def evaluate_regression_bundle(
    bundle: RegressionResearchBundle,
    frame: pd.DataFrame,
    training: TrainingConfig,
) -> dict[str, Any]:
    prediction = np.asarray(bundle.model.predict(_pool(frame, bundle.feature_set, label=False)), dtype=float)
    actual = frame["net_return"].to_numpy(dtype=float)
    selected = prediction >= bundle.threshold
    selected_frame = frame.reset_index(drop=True).loc[selected]
    wins = selected_frame.loc[selected_frame["net_return"] > 0, "net_return"].sum() if len(selected_frame) else 0.0
    losses = abs(selected_frame.loc[selected_frame["net_return"] < 0, "net_return"].sum()) if len(selected_frame) else 0.0
    portfolio = {
        "cost_1x": run_portfolio_backtest(frame, prediction, bundle.threshold, cost_multiplier=1.0, **_backtest_kwargs(training)),
        "cost_1_5x": run_portfolio_backtest(frame, prediction, bundle.threshold, cost_multiplier=1.5, **_backtest_kwargs(training)),
        "cost_2x": run_portfolio_backtest(frame, prediction, bundle.threshold, cost_multiplier=2.0, **_backtest_kwargs(training)),
    }
    correlation = float(np.corrcoef(actual, prediction)[0, 1]) if len(actual) > 1 and np.std(actual) > 0 and np.std(prediction) > 0 else None
    return {
        "regression": {
            "rmse": float(math.sqrt(mean_squared_error(actual, prediction))),
            "mae": float(mean_absolute_error(actual, prediction)),
            "correlation": correlation,
            "prediction_mean": float(np.mean(prediction)),
            "prediction_std": float(np.std(prediction)),
        },
        "trading": {
            "trades": int(selected.sum()),
            "selected_rate": float(selected.mean()),
            "mean_net_return": float(selected_frame["net_return"].mean()) if len(selected_frame) else None,
            "total_net_return": float(selected_frame["net_return"].sum()) if len(selected_frame) else 0.0,
            "profit_factor": float(wins / losses) if losses > 0 else (float("inf") if wins > 0 else None),
        },
        "portfolio": portfolio,
        "threshold": float(bundle.threshold),
    }


def regression_economic_score(metrics: dict[str, Any]) -> float:
    portfolio = metrics["portfolio"]
    base = portfolio["cost_1x"]
    stress = portfolio["cost_1_5x"]
    stress2 = portfolio["cost_2x"]
    return float(
        6.0 * float(base.get("portfolio_return") or 0.0)
        + 3.0 * float(stress.get("portfolio_return") or 0.0)
        + 1.0 * float(stress2.get("portfolio_return") or 0.0)
        + 0.3 * min(float(base.get("profit_factor") or 0.0) - 1.0, 2.0)
        - 1.5 * abs(min(float(base.get("maximum_drawdown") or 0.0), 0.0))
    )

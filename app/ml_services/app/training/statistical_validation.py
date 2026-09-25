from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_score, roc_auc_score

from ..backtesting.simulator import run_portfolio_backtest
from .evaluate_model import threshold_array


def _interval_delta(interval: str) -> pd.Timedelta:
    value = interval.strip().lower()
    amount = int(value[:-1])
    return {
        "m": pd.Timedelta(minutes=amount),
        "h": pd.Timedelta(hours=amount),
        "d": pd.Timedelta(days=amount),
    }[value[-1]]


def _ci(values: list[float]) -> dict[str, float | None]:
    clean = np.asarray([value for value in values if np.isfinite(value)], dtype=float)
    if not len(clean):
        return {"lower_95": None, "median": None, "upper_95": None}
    return {
        "lower_95": float(np.quantile(clean, 0.025)),
        "median": float(np.quantile(clean, 0.50)),
        "upper_95": float(np.quantile(clean, 0.975)),
    }


def _block_sample(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    *,
    block_size: int,
    rng: np.random.Generator,
    interval: str,
) -> tuple[pd.DataFrame, np.ndarray]:
    source = frame.copy().reset_index(drop=True)
    source["_source_index"] = np.arange(len(source))
    source["timestamp"] = pd.to_datetime(source["timestamp"])
    timestamps = pd.Index(source["timestamp"].drop_duplicates().sort_values())
    if len(timestamps) < 2:
        return source.drop(columns=["_source_index"]), probabilities.copy()
    chosen: list[pd.Timestamp] = []
    max_start = max(len(timestamps) - block_size, 0)
    while len(chosen) < len(timestamps):
        start = int(rng.integers(0, max_start + 1))
        chosen.extend(timestamps[start : start + block_size].tolist())
    chosen = chosen[: len(timestamps)]
    delta = _interval_delta(interval)
    base = timestamps[0]
    parts: list[pd.DataFrame] = []
    sampled_probabilities: list[float] = []
    for position, timestamp in enumerate(chosen):
        part = source[source["timestamp"] == timestamp].copy()
        if part.empty:
            continue
        sampled_probabilities.extend(
            probabilities[part["_source_index"].to_numpy(dtype=int)].tolist()
        )
        part["timestamp"] = base + delta * position
        parts.append(part)
    sampled = pd.concat(parts, ignore_index=True).drop(columns=["_source_index"])
    return sampled, np.asarray(sampled_probabilities, dtype=float)


def block_bootstrap_report(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    thresholds: dict[str, float] | float,
    *,
    interval: str,
    base_round_trip_cost: float,
    iterations: int = 100,
    block_size: int = 24,
    random_seed: int = 42,
    backtest_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Moving-block bootstrap preserving short-run time dependence."""
    if iterations < 1:
        return {"iterations": 0, "reason": "bootstrap disabled"}
    rng = np.random.default_rng(random_seed)
    stats: dict[str, list[float]] = {
        "roc_auc": [],
        "pr_auc": [],
        "precision": [],
        "win_rate": [],
        "mean_trade_return": [],
        "profit_factor": [],
        "portfolio_return": [],
        "sharpe": [],
    }
    kwargs = dict(backtest_kwargs or {})
    for _ in range(iterations):
        sampled, sampled_p = _block_sample(
            frame,
            probabilities,
            block_size=block_size,
            rng=rng,
            interval=interval,
        )
        y = sampled["target_good_trade"].to_numpy(dtype=int)
        threshold_values = threshold_array(sampled, thresholds)
        predicted = sampled_p >= threshold_values
        if np.unique(y).size == 2:
            stats["roc_auc"].append(float(roc_auc_score(y, sampled_p)))
            stats["pr_auc"].append(float(average_precision_score(y, sampled_p)))
        stats["precision"].append(float(precision_score(y, predicted, zero_division=0)))
        selected = sampled[predicted]
        if not selected.empty:
            returns = selected["net_return"].to_numpy(dtype=float)
            stats["win_rate"].append(float(np.mean(returns > 0)))
            stats["mean_trade_return"].append(float(np.mean(returns)))
            wins = float(returns[returns > 0].sum())
            losses = abs(float(returns[returns < 0].sum()))
            if losses > 0:
                stats["profit_factor"].append(wins / losses)
        portfolio = run_portfolio_backtest(
            sampled,
            sampled_p,
            thresholds,
            interval=interval,
            base_round_trip_cost=base_round_trip_cost,
            **kwargs,
        )
        stats["portfolio_return"].append(float(portfolio["portfolio_return"]))
        if portfolio.get("sharpe") is not None:
            stats["sharpe"].append(float(portfolio["sharpe"]))
    return {
        "method": "moving_block_bootstrap",
        "iterations": iterations,
        "block_size_bars": block_size,
        "confidence_intervals": {name: _ci(values) for name, values in stats.items()},
    }

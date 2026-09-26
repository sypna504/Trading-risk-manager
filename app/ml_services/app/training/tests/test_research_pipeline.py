from __future__ import annotations

import numpy as np
import pandas as pd

from app.features_builder import CAT_FEATURES, FEATURE_COLUMNS
from app.research.features import FeatureSet, augment_market_context
from app.research.modeling import build_bundle, evaluate_bundle
from app.research.regression import evaluate_regression_bundle, fit_regression_bundle
from app.research.splits import split_deployment_dataset, split_research_dataset
from app.training.build_dataset import _apply_horizon_return_target
from app.training.training_config import TrainingConfig


def _research_frame(hours: int = 1200) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    timestamps = pd.date_range("2026-01-01", periods=hours, freq="h")
    rows = []
    for i, timestamp in enumerate(timestamps):
        for symbol_index, symbol in enumerate(("BTCUSDT", "ETHUSDT")):
            strategy = "breakout" if (i + symbol_index) % 2 == 0 else "mean_reversion"
            latent = np.sin(i / 11.0) + (0.4 if symbol == "BTCUSDT" else -0.1) + rng.normal(0, 0.6)
            target = int(latent > 0.35)
            row = {
                "timestamp": timestamp,
                "symbol": symbol,
                "strategy_name": strategy,
                "interval": "1h",
                "volatility_regime": "high" if i % 5 == 0 else "low",
                "trend_regime": "up" if i % 3 == 0 else "range",
                "entry_price": 100.0,
                "stop_loss_fraction": 0.01,
                "holding_bars": 3.0,
                "target_good_trade": target,
                "net_return": 0.017 if target else -0.011,
                "exit_price": 101.7 if target else 98.9,
                "exit_reason": "take_profit" if target else "stop_loss",
            }
            for column in FEATURE_COLUMNS:
                if column in row:
                    continue
                if column in CAT_FEATURES:
                    row[column] = "x"
                elif column == "candle_duration_minutes":
                    row[column] = 60.0
                elif column == "rsi_14":
                    row[column] = 50.0 + 12.0 * latent
                elif column == "atr_14_pct":
                    row[column] = 0.01 + 0.002 * abs(latent)
                elif column in {"ret_1", "ret_1h", "ret_3h", "ema_distance_20"}:
                    row[column] = 0.01 * latent
                else:
                    row[column] = float(rng.normal(0, 0.3))
            rows.append(row)
    return pd.DataFrame(rows)


def _tiny_feature_set() -> FeatureSet:
    columns = (
        "symbol",
        "strategy_name",
        "interval",
        "volatility_regime",
        "trend_regime",
        "ret_1",
        "ret_3h",
        "rsi_14",
        "atr_14_pct",
        "ema_distance_20",
    )
    cats = tuple(column for column in columns if column in CAT_FEATURES)
    return FeatureSet("tiny", columns, cats, True)


def _training() -> TrainingConfig:
    return TrainingConfig(
        symbols=["BTCUSDT", "ETHUSDT"],
        required_symbols=["BTCUSDT", "ETHUSDT"],
        early_stopping_rounds=15,
        minimum_selected_trades=10,
        minimum_strategy_selected_trades=5,
        bootstrap_iterations=5,
    )


def test_research_split_keeps_final_holdout_untouched_and_purged():
    frame = _research_frame(1200)
    purge = pd.Timedelta(hours=4)
    split = split_research_dataset(frame, final_holdout_days=14, purge=purge)

    assert split.final_holdout["timestamp"].min() >= pd.Timestamp(split.metadata["holdout_start"])
    ordered = [
        split.train,
        split.model_selection,
        split.calibration_fit,
        split.calibration_selection,
        split.threshold_selection,
        split.development_oos,
    ]
    for left, right in zip(ordered[:-1], ordered[1:]):
        assert left["timestamp"].max() < right["timestamp"].min() - purge
    assert split.development_oos["timestamp"].max() < split.final_holdout["timestamp"].min() - purge


def test_deployment_split_is_chronological_and_has_no_oos_claim():
    frame = _research_frame(800)
    split = split_deployment_dataset(frame, purge=pd.Timedelta(hours=4))
    assert split.metadata["production_refit"] is True
    assert split.development_oos.empty
    assert split.final_holdout.empty
    assert split.train["timestamp"].max() < split.model_selection["timestamp"].min() - pd.Timedelta(hours=4)


def test_horizon_target_has_ex_ante_risk_fields_for_portfolio_backtest():
    timestamps = pd.date_range("2026-01-01", periods=12, freq="h")
    features = pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": "BTCUSDT",
            "interval": "1h",
            "open": np.linspace(100, 111, 12),
            "high": np.linspace(101, 112, 12),
            "low": np.linspace(99, 110, 12),
            "close": np.linspace(100.5, 111.5, 12),
            "atr_14_pct": 0.01,
        }
    )
    config = _training()
    config.target_definition = "horizon_return_drawdown"
    result = _apply_horizon_return_target(features, config)
    usable = result.iloc[:-config.target_horizon_bars]
    assert np.isfinite(usable["stop_loss_fraction"]).all()
    assert (usable["stop_loss_fraction"] > 0).all()
    assert np.isfinite(usable["stop_loss_price"]).all()
    assert np.isfinite(usable["take_profit_price"]).all()


def test_market_context_is_causal_for_prior_timestamp():
    timestamps = pd.date_range("2026-01-01", periods=180, freq="h", tz="UTC")
    rows = []
    for symbol, multiplier in (("BTCUSDT", 1.0), ("ETHUSDT", 0.6)):
        for i, timestamp in enumerate(timestamps):
            close = 100 + multiplier * i * 0.05 + np.sin(i / 7)
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "interval": "1h",
                    "open": close * 0.999,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1000 + 5 * i + (100 if symbol == "BTCUSDT" else 0),
                }
            )
    history = pd.DataFrame(rows)
    dataset = pd.DataFrame(
        [
            {"timestamp": timestamps[140].tz_convert(None), "symbol": "ETHUSDT", "interval": "1h"},
            {"timestamp": timestamps[150].tz_convert(None), "symbol": "BTCUSDT", "interval": "1h"},
        ]
    )
    before = augment_market_context(dataset, history)
    changed = history.copy()
    mask = (changed["symbol"] == "BTCUSDT") & (changed["timestamp"] == timestamps[-1])
    changed.loc[mask, "close"] *= 2.0
    changed.loc[mask, "high"] = changed.loc[mask, ["high", "close"]].max(axis=1) * 1.01
    changed.loc[mask, "low"] = changed.loc[mask, ["low", "open", "close"]].min(axis=1) * 0.99
    after = augment_market_context(dataset, changed)
    context_columns = [column for column in before.columns if column.startswith("btc_") or column.startswith("relative_") or column.startswith("xs_")]
    prior_before = before.loc[before["timestamp"] == timestamps[140].tz_convert(None), context_columns].reset_index(drop=True)
    prior_after = after.loc[after["timestamp"] == timestamps[140].tz_convert(None), context_columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(prior_before, prior_after, check_dtype=False)


def test_research_bundle_separates_calibration_threshold_and_reports_expected_utility():
    frame = _research_frame(1200)
    split = split_research_dataset(frame, final_holdout_days=14, purge=pd.Timedelta(hours=4))
    training = _training()
    params = {"name": "test", "iterations": 80, "learning_rate": 0.08, "depth": 3, "l2_leaf_reg": 5.0}
    bundle, selection = build_bundle(
        split,
        _tiny_feature_set(),
        params,
        42,
        "none",
        "pooled",
        training,
    )
    metrics = evaluate_bundle(bundle, split.development_oos, training)
    assert selection["calibration"]
    assert selection["threshold_selection"]
    assert metrics["expected_utility"]["reference"]
    assert "cost_1_5x" in metrics["portfolio"]
    assert "cost_2x" in metrics["portfolio"]
    assert metrics["classification"]["roc_auc"] is not None


def test_symbol_specific_research_architecture_runs_only_with_sufficient_groups():
    frame = _research_frame(1200)
    split = split_research_dataset(frame, final_holdout_days=14, purge=pd.Timedelta(hours=4))
    params = {"name": "test", "iterations": 50, "learning_rate": 0.1, "depth": 3, "l2_leaf_reg": 5.0}
    bundle, _ = build_bundle(split, _tiny_feature_set(), params, 42, "none", "separate_symbol", _training())
    assert {"BTCUSDT", "ETHUSDT"}.issubset(set(bundle.models))
    assert "__fallback__" in bundle.models


def test_regression_research_uses_threshold_selection_and_evaluates_oos():
    frame = _research_frame(1200)
    split = split_research_dataset(frame, final_holdout_days=14, purge=pd.Timedelta(hours=4))
    params = {"name": "test", "iterations": 60, "learning_rate": 0.08, "depth": 3, "l2_leaf_reg": 5.0}
    bundle, selection = fit_regression_bundle(split, _tiny_feature_set(), params, 42, _training())
    metrics = evaluate_regression_bundle(bundle, split.development_oos, _training())
    assert "threshold_selection" in selection
    assert metrics["regression"]["rmse"] >= 0
    assert "cost_2x" in metrics["portfolio"]


def test_market_feature_sets_have_only_present_categorical_columns():
    from app.research.features import feature_sets

    for feature_set in feature_sets(include_market_context=True):
        assert set(feature_set.cat_features).issubset(set(feature_set.columns))


def test_portfolio_backtest_handles_threshold_selecting_zero_rows():
    from app.backtesting.simulator import run_portfolio_backtest

    frame = _research_frame(20)
    probabilities = np.zeros(len(frame), dtype=float)
    result = run_portfolio_backtest(
        frame,
        probabilities,
        1.0,
        interval="1h",
    )
    assert result["trades"] == 0
    assert result["portfolio_return"] == 0.0
    assert result["ending_capital"] == result["starting_capital"]

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..features_builder import CAT_FEATURES, FEATURE_COLUMNS, calculate_features


PRODUCTION_GROUPS: dict[str, list[str]] = {
    "momentum": [
        "ret_1", "ret_7", "ret_20", "ret_50", "ret_1h", "ret_3h", "ret_12h", "ret_24h",
        "return_per_hour", "ema_distance_20", "ema_distance_50", "ema_slope_20",
        "momentum_acceleration", "distance_to_high_50", "distance_to_low_50",
    ],
    "volatility": [
        "vol_7", "vol_20", "vol_50", "volatility_per_sqrt_hour", "downside_vol_20",
        "atr_14_pct", "atr_per_sqrt_hour", "vol_ratio_7_50", "vol_ratio_20_50", "rolling_drawdown_50",
    ],
    "volume": [
        "volume_z_20", "volume_z_50", "volume_per_hour", "volume_trend_20",
        "dollar_volume_z_50", "log_dollar_volume",
    ],
    "mean_reversion": ["price_z_20", "price_z_50", "rsi_14", "bollinger_position_20"],
    "regime": ["volatility_regime", "trend_regime"],
    "identity": ["symbol", "strategy_name", "interval"],
    "structure": ["candle_duration_minutes", "candle_range", "body_size"],
}

BTC_CONTEXT = [
    "btc_ret_1h",
    "btc_ret_3h",
    "btc_ret_12h",
    "btc_ret_24h",
    "btc_vol_6h",
    "btc_vol_24h",
    "btc_atr_pct",
    "btc_drawdown_50",
    "btc_ema_distance_50",
    "btc_trend_regime",
    "btc_volatility_regime",
]
RELATIVE_CONTEXT = [
    "relative_ret_1h",
    "relative_ret_3h",
    "relative_ret_12h",
    "rolling_beta_btc_24",
    "rolling_corr_btc_24",
    "relative_volatility_20",
    "relative_strength_btc_12h",
]
CROSS_SECTIONAL = [
    "xs_return_rank_3h",
    "xs_volume_rank_20",
    "xs_momentum_rank",
    "xs_volatility_rank_20",
    "xs_distance_high_rank",
    "xs_liquidity_rank",
    "liquidity_bucket",
]
BTC_CAT_FEATURES = ["btc_trend_regime", "btc_volatility_regime"]
MARKET_CAT_FEATURES = [*BTC_CAT_FEATURES, "liquidity_bucket"]


@dataclass(frozen=True, slots=True)
class FeatureSet:
    name: str
    columns: tuple[str, ...]
    cat_features: tuple[str, ...]
    production_compatible: bool


def _rolling_market_relatives(part: pd.DataFrame, window: int = 24) -> pd.DataFrame:
    result = part.sort_values("timestamp").copy()
    asset = pd.to_numeric(result["ret_1h"], errors="coerce")
    market = pd.to_numeric(result["btc_ret_1h"], errors="coerce")
    covariance = asset.rolling(window, min_periods=max(window // 2, 6)).cov(market)
    variance = market.rolling(window, min_periods=max(window // 2, 6)).var()
    result["rolling_beta_btc_24"] = covariance / variance.replace(0, np.nan)
    result["rolling_corr_btc_24"] = asset.rolling(window, min_periods=max(window // 2, 6)).corr(market)
    return result


def augment_market_context(dataset: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Add causal market-relative/cross-sectional research features.

    Every derived value uses only the same timestamp or earlier candles. No
    backward/forward fills are used. The production inference contract is not
    changed by this helper; feature sets using these columns are explicitly
    marked non-production-compatible until online market context is implemented.
    """
    raw = history.copy()
    if "interval" not in raw.columns:
        raw["interval"] = "1h"
    full = calculate_features(raw)
    full["timestamp"] = pd.to_datetime(full["timestamp"])
    full = full.sort_values(["symbol", "interval", "timestamp"]).reset_index(drop=True)

    btc = full[full["symbol"] == "BTCUSDT"].copy()
    if btc.empty:
        raise ValueError("BTCUSDT history is required for market-context research")
    btc["btc_vol_6h"] = btc["ret_1h"].rolling(6, min_periods=3).std()
    btc["btc_vol_24h"] = btc["ret_1h"].rolling(24, min_periods=12).std()
    btc_context = btc[
        [
            "timestamp", "interval", "ret_1h", "ret_3h", "ret_12h", "ret_24h",
            "btc_vol_6h", "btc_vol_24h", "atr_14_pct", "rolling_drawdown_50",
            "ema_distance_50", "trend_regime", "volatility_regime",
        ]
    ].rename(
        columns={
            "ret_1h": "btc_ret_1h",
            "ret_3h": "btc_ret_3h",
            "ret_12h": "btc_ret_12h",
            "ret_24h": "btc_ret_24h",
            "atr_14_pct": "btc_atr_pct",
            "rolling_drawdown_50": "btc_drawdown_50",
            "ema_distance_50": "btc_ema_distance_50",
            "trend_regime": "btc_trend_regime",
            "volatility_regime": "btc_volatility_regime",
        }
    )

    enriched = full.merge(btc_context, on=["timestamp", "interval"], how="left", validate="many_to_one")
    enriched["relative_ret_1h"] = enriched["ret_1h"] - enriched["btc_ret_1h"]
    enriched["relative_ret_3h"] = enriched["ret_3h"] - enriched["btc_ret_3h"]
    enriched["relative_ret_12h"] = enriched["ret_12h"] - enriched["btc_ret_12h"]
    enriched["relative_volatility_20"] = enriched["vol_20"] / enriched["btc_vol_24h"].replace(0, np.nan)
    enriched["relative_strength_btc_12h"] = enriched["ret_12h"] - enriched["btc_ret_12h"]
    enriched = pd.concat(
        [_rolling_market_relatives(part) for _, part in enriched.groupby(["symbol", "interval"], sort=False)],
        ignore_index=True,
    )

    # Cross-sectional ranks use only values observed at timestamp t across the
    # configured universe. Ranking never reads t+1 or future bars.
    rank_map = {
        "ret_3h": "xs_return_rank_3h",
        "volume_z_20": "xs_volume_rank_20",
        "momentum_acceleration": "xs_momentum_rank",
        "vol_20": "xs_volatility_rank_20",
        "distance_to_high_50": "xs_distance_high_rank",
        "log_dollar_volume": "xs_liquidity_rank",
    }
    for source, target in rank_map.items():
        enriched[target] = enriched.groupby(["timestamp", "interval"])[source].rank(pct=True, method="average")
    enriched["liquidity_bucket"] = pd.cut(
        enriched["xs_liquidity_rank"],
        bins=[-np.inf, 1 / 3, 2 / 3, np.inf],
        labels=["low", "medium", "high"],
        include_lowest=True,
    ).astype("object")

    context_columns = [
        "timestamp", "symbol", "interval", *BTC_CONTEXT, *RELATIVE_CONTEXT, *CROSS_SECTIONAL
    ]
    context = enriched[context_columns].drop_duplicates(["timestamp", "symbol", "interval"])
    result = dataset.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"])
    result = result.merge(context, on=["timestamp", "symbol", "interval"], how="left", validate="many_to_one")
    return result


def feature_sets(include_market_context: bool = True) -> list[FeatureSet]:
    sets: list[FeatureSet] = [
        FeatureSet("production_full", tuple(FEATURE_COLUMNS), tuple(CAT_FEATURES), True),
    ]
    for group_name in ["momentum", "volatility", "volume", "mean_reversion", "regime", "identity"]:
        dropped = set(PRODUCTION_GROUPS[group_name])
        columns = tuple(column for column in FEATURE_COLUMNS if column not in dropped)
        cats = tuple(column for column in CAT_FEATURES if column in columns)
        sets.append(FeatureSet(f"minus_{group_name}", columns, cats, True))
    if include_market_context:
        market_columns = tuple([*FEATURE_COLUMNS, *BTC_CONTEXT, *RELATIVE_CONTEXT])
        market_cats = tuple([*CAT_FEATURES, *BTC_CAT_FEATURES])
        sets.append(FeatureSet("production_plus_btc", market_columns, market_cats, False))
        cross_columns = tuple([*FEATURE_COLUMNS, *BTC_CONTEXT, *RELATIVE_CONTEXT, *CROSS_SECTIONAL])
        cross_cats = tuple([*CAT_FEATURES, *MARKET_CAT_FEATURES])
        sets.append(FeatureSet("production_plus_market_context", cross_columns, cross_cats, False))
    return sets


def drop_incomplete(frame: pd.DataFrame, feature_set: FeatureSet) -> pd.DataFrame:
    required = [*feature_set.columns, "target_good_trade", "net_return", "entry_price", "exit_price", "timestamp"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"research frame missing feature columns: {missing}")
    cleaned = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    return cleaned

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .training.target_config import interval_to_minutes


MIN_CANDLES = 60
FEATURE_SCHEMA_VERSION = "v3"

FEATURE_COLUMNS = [
    "symbol",
    "strategy_name",
    "interval",
    "volatility_regime",
    "trend_regime",
    "candle_duration_minutes",
    "ret_1",
    "ret_7",
    "ret_20",
    "ret_50",
    "ret_1h",
    "ret_3h",
    "ret_12h",
    "ret_24h",
    "return_per_hour",
    "vol_7",
    "vol_20",
    "vol_50",
    "volatility_per_sqrt_hour",
    "downside_vol_20",
    "volume_z_20",
    "volume_z_50",
    "volume_per_hour",
    "volume_trend_20",
    "price_z_20",
    "price_z_50",
    "candle_range",
    "body_size",
    "rsi_14",
    "atr_14_pct",
    "atr_per_sqrt_hour",
    "distance_to_high_50",
    "distance_to_low_50",
    "rolling_drawdown_50",
    "vol_ratio_7_50",
    "vol_ratio_20_50",
    "dollar_volume_z_50",
    "log_dollar_volume",
    "ema_distance_20",
    "ema_distance_50",
    "ema_slope_20",
    "bollinger_position_20",
    "momentum_acceleration",
]

CAT_FEATURES = [
    "symbol",
    "strategy_name",
    "interval",
    "volatility_regime",
    "trend_regime",
]

REQUIRED_CANDLE_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "symbol",
]
NUMERIC_CANDLE_COLUMNS = ["open", "high", "low", "close", "volume"]


def normalize_symbol(symbol: str) -> str:
    return str(symbol).upper().replace("/", "").replace("-", "").strip()


def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mean) / std.replace(0, np.nan)


def _bars_for_minutes(minutes: int, interval: str) -> int:
    candle_minutes = interval_to_minutes(interval)
    return max(int(round(minutes / candle_minutes)), 1)


def _validate_candle_frame(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("candle frame is empty")
    if df["timestamp"].isna().any():
        raise ValueError("candles contain invalid timestamps")
    if (df["symbol"] == "").any():
        raise ValueError("candles contain an empty symbol")
    if df.duplicated(["symbol", "interval", "timestamp"]).any():
        raise ValueError("candles contain duplicate symbol+interval+timestamp rows")
    values = df[NUMERIC_CANDLE_COLUMNS].to_numpy(dtype=float)
    if np.isnan(values).any() or np.isinf(values).any():
        raise ValueError("OHLCV values must be finite")
    if (df[["open", "high", "low", "close"]] <= 0).any(axis=None):
        raise ValueError("OHLC values must be positive")
    if (df["volume"] < 0).any():
        raise ValueError("volume must be non-negative")
    if (
        (df["high"] < df[["open", "close", "low"]].max(axis=1)).any()
        or (df["low"] > df[["open", "close", "high"]].min(axis=1)).any()
    ):
        raise ValueError("OHLC invariants failed")


def calculate_symbol_features(symbol_df: pd.DataFrame) -> pd.DataFrame:
    df = symbol_df.sort_values("timestamp").copy()
    if "interval" not in df.columns:
        df["interval"] = "1h"
    interval = str(df["interval"].iloc[0])
    candle_minutes = interval_to_minutes(interval)
    duration_hours = candle_minutes / 60.0
    close = df["close"]
    volume = df["volume"]

    df["candle_duration_minutes"] = float(candle_minutes)
    df["ret_1"] = close.pct_change(1)
    for window in (7, 20, 50):
        df[f"ret_{window}"] = close.pct_change(window)
        df[f"vol_{window}"] = df["ret_1"].rolling(window).std()

    for label, minutes in (("1h", 60), ("3h", 180), ("12h", 720), ("24h", 1440)):
        df[f"ret_{label}"] = close.pct_change(_bars_for_minutes(minutes, interval))

    df["return_per_hour"] = df["ret_1"] / max(duration_hours, 1e-12)
    df["volatility_per_sqrt_hour"] = df["vol_20"] / math.sqrt(max(duration_hours, 1e-12))
    df["downside_vol_20"] = df["ret_1"].clip(upper=0).rolling(20).std()

    df["volume_z_20"] = rolling_zscore(volume, 20)
    df["volume_z_50"] = rolling_zscore(volume, 50)
    df["volume_per_hour"] = volume / max(duration_hours, 1e-12)
    volume_ma_5 = volume.rolling(5).mean()
    volume_ma_20 = volume.rolling(20).mean()
    df["volume_trend_20"] = volume_ma_5 / volume_ma_20.replace(0, np.nan) - 1

    df["price_z_20"] = rolling_zscore(close, 20)
    df["price_z_50"] = rolling_zscore(close, 50)
    df["high_20"] = df["high"].rolling(20).max().shift(1)
    df["high_50"] = df["high"].rolling(50).max().shift(1)
    df["low_50"] = df["low"].rolling(50).min().shift(1)
    df["candle_range"] = (df["high"] - df["low"]) / close
    df["body_size"] = (df["close"] - df["open"]).abs() / df["open"]

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr_14"] = true_range.rolling(14).mean()
    df["atr_14_pct"] = df["atr_14"] / close
    df["atr_per_sqrt_hour"] = df["atr_14_pct"] / math.sqrt(max(duration_hours, 1e-12))

    df["distance_to_high_50"] = close / df["high_50"] - 1
    df["distance_to_low_50"] = close / df["low_50"] - 1
    rolling_max_50 = close.rolling(50).max()
    df["rolling_drawdown_50"] = close / rolling_max_50 - 1
    df["vol_ratio_7_50"] = df["vol_7"] / (df["vol_50"] + 1e-12)
    df["vol_ratio_20_50"] = df["vol_20"] / (df["vol_50"] + 1e-12)

    df["dollar_volume"] = close * volume
    df["dollar_volume_z_50"] = rolling_zscore(df["dollar_volume"], 50)
    df["log_dollar_volume"] = np.log1p(df["dollar_volume"])

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.rolling(14).mean()
    average_loss = loss.rolling(14).mean()
    relative_strength = average_gain / (average_loss + 1e-12)
    df["rsi_14"] = 100 - 100 / (1 + relative_strength)

    ema_20 = close.ewm(span=20, adjust=False).mean()
    ema_50 = close.ewm(span=50, adjust=False).mean()
    df["ema_distance_20"] = close / ema_20 - 1
    df["ema_distance_50"] = close / ema_50 - 1
    df["ema_slope_20"] = ema_20.pct_change(3) / 3
    middle = close.rolling(20).mean()
    band_std = close.rolling(20).std()
    df["bollinger_position_20"] = (close - middle) / (2 * band_std.replace(0, np.nan))
    df["momentum_acceleration"] = df["ret_7"] - df["ret_20"] * (7 / 20)

    vol_median = df["vol_50"].rolling(100, min_periods=50).median()
    df["volatility_regime"] = np.where(df["vol_20"] > vol_median, "high", "low")
    df["trend_regime"] = np.select(
        [df["ema_distance_50"] > 0.01, df["ema_distance_50"] < -0.01],
        ["up", "down"],
        default="range",
    )

    df["hour"] = df["timestamp"].dt.hour.astype(str)
    df["weekday"] = df["timestamp"].dt.weekday.astype(str)
    df["signal_breakout"] = (
        (close > df["high_20"])
        & (df["volume_z_20"] > 0.5)
        & (df["ema_slope_20"] > 0)
    ).astype(int)
    df["signal_mean_reversion"] = (
        (df["rsi_14"] < 35)
        & (df["price_z_20"] < -1)
        & (df["distance_to_low_50"] < 0.05)
    ).astype(int)
    return df


def calculate_features(candles_df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_CANDLE_COLUMNS if column not in candles_df.columns]
    if missing:
        raise ValueError(f"missing candle columns: {missing}")
    df = candles_df.copy()
    if "interval" not in df.columns:
        df["interval"] = "1h"
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
    df["symbol"] = df["symbol"].map(normalize_symbol)
    df["interval"] = df["interval"].astype(str)
    for interval in df["interval"].unique():
        interval_to_minutes(str(interval))
    for column in NUMERIC_CANDLE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df = df.sort_values(["symbol", "interval", "timestamp"]).reset_index(drop=True)
    _validate_candle_frame(df)
    parts = [
        calculate_symbol_features(part)
        for _, part in df.groupby(["symbol", "interval"], sort=False)
    ]
    return pd.concat(parts, ignore_index=True).replace([np.inf, -np.inf], np.nan)


def latest_complete_feature_row(
    features_df: pd.DataFrame,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Return the latest row complete for the requested contract.

    ``required_columns`` keeps compatibility with backend signal detection, while
    the default remains the production ML feature schema.
    """
    if features_df.empty:
        raise ValueError("feature frame is empty")

    required = list(required_columns or FEATURE_COLUMNS)
    absent = [column for column in required if column not in features_df.columns]
    if absent:
        raise ValueError(f"feature frame is missing columns: {absent}")

    complete = features_df.dropna(subset=required)
    if complete.empty:
        missing = [column for column in required if features_df[column].isna().all()]
        raise ValueError(f"could not calculate a complete feature row; missing={missing}")
    return complete.sort_values("timestamp").iloc[[-1]].copy()


def build_inference_features(
    candles: list[dict],
    symbol: str,
    strategy_name: str,
    interval: str = "1h",
) -> pd.DataFrame:
    if len(candles) < MIN_CANDLES:
        raise ValueError(f"at least {MIN_CANDLES} candles are required")
    candles_df = pd.DataFrame(candles)
    candles_df["symbol"] = normalize_symbol(symbol)
    candles_df["interval"] = interval
    features_df = calculate_features(candles_df)
    features_df["strategy_name"] = strategy_name
    # Keep the full calculated row. The predictor selects the exact columns from
    # the loaded model config. This allows a legacy v2 champion to remain usable
    # while a v3 candidate is trained and evaluated.
    result = latest_complete_feature_row(features_df, FEATURE_COLUMNS).copy()
    for column in CAT_FEATURES:
        result[column] = result[column].astype(str)
    return result

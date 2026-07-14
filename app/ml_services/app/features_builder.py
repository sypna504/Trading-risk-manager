from __future__ import annotations

import numpy as np
import pandas as pd


MIN_CANDLES = 60

FEATURE_COLUMNS = [
    "symbol",
    "strategy_name",
    "ret_1",
    "ret_7",
    "ret_20",
    "ret_50",
    "vol_7",
    "vol_20",
    "vol_50",
    "volume_z_20",
    "volume_z_50",
    "price_z_20",
    "price_z_50",
    "candle_range",
    "body_size",
    "rsi_14",
    "atr_14_pct",
    "distance_to_high_50",
    "distance_to_low_50",
    "vol_ratio_7_50",
    "vol_ratio_20_50",
    "dollar_volume_z_50",
    "log_dollar_volume",
    "hour",
    "weekday",
]

CAT_FEATURES = [
    "symbol",
    "strategy_name",
    "hour",
    "weekday",
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


def normalize_symbol(symbol: str) -> str:
    return (
        str(symbol)
        .upper()
        .replace("/", "")
        .replace("-", "")
        .strip()
    )


def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()

    return (
        (series - rolling_mean)
        / rolling_std.replace(0, np.nan)
    )


def calculate_symbol_features(
    symbol_df: pd.DataFrame,
) -> pd.DataFrame:
    df = symbol_df.sort_values("timestamp").copy()

    close = df["close"]
    volume = df["volume"]

    df["ret_1"] = close.pct_change(1)

    for window in (7, 20, 50):
        df[f"ret_{window}"] = close.pct_change(window)

        df[f"vol_{window}"] = (
            df["ret_1"]
            .rolling(window)
            .std()
        )

    df["volume_z_20"] = rolling_zscore(
        volume,
        20,
    )
    df["volume_z_50"] = rolling_zscore(
        volume,
        50,
    )

    df["price_z_20"] = rolling_zscore(
        close,
        20,
    )
    df["price_z_50"] = rolling_zscore(
        close,
        50,
    )

    df["high_20"] = (
        df["high"]
        .rolling(20)
        .max()
        .shift(1)
    )

    df["high_50"] = (
        df["high"]
        .rolling(50)
        .max()
        .shift(1)
    )

    df["low_50"] = (
        df["low"]
        .rolling(50)
        .min()
        .shift(1)
    )

    df["candle_range"] = (
        (df["high"] - df["low"])
        / df["close"]
    )

    df["body_size"] = (
        (df["close"] - df["open"]).abs()
        / df["open"]
    )

    previous_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["atr_14"] = true_range.rolling(14).mean()

    df["atr_14_pct"] = (
        df["atr_14"]
        / df["close"]
    )

    df["distance_to_high_50"] = (
        df["close"]
        / df["high_50"]
        - 1
    )

    df["distance_to_low_50"] = (
        df["close"]
        / df["low_50"]
        - 1
    )

    df["vol_ratio_7_50"] = (
        df["vol_7"]
        / (df["vol_50"] + 1e-12)
    )

    df["vol_ratio_20_50"] = (
        df["vol_20"]
        / (df["vol_50"] + 1e-12)
    )

    df["dollar_volume"] = (
        df["close"]
        * df["volume"]
    )

    df["dollar_volume_z_50"] = rolling_zscore(
        df["dollar_volume"],
        50,
    )

    df["log_dollar_volume"] = np.log1p(
        df["dollar_volume"]
    )

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.rolling(14).mean()
    average_loss = loss.rolling(14).mean()

    relative_strength = (
        average_gain
        / (average_loss + 1e-12)
    )

    df["rsi_14"] = (
        100
        - 100 / (1 + relative_strength)
    )

    df["hour"] = (
        df["timestamp"]
        .dt.hour
        .astype(str)
    )

    df["weekday"] = (
        df["timestamp"]
        .dt.weekday
        .astype(str)
    )

    df["signal_breakout"] = (
        (df["close"] > df["high_20"])
        & (df["volume_z_20"] > 0.5)
    ).astype(int)

    df["signal_mean_reversion"] = (
        (df["rsi_14"] < 35)
        & (df["price_z_20"] < -1)
    ).astype(int)

    return df


def calculate_features(
    candles_df: pd.DataFrame,
) -> pd.DataFrame:
    missing_columns = [
        column
        for column in REQUIRED_CANDLE_COLUMNS
        if column not in candles_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"missing candle columns: {missing_columns}"
        )

    df = candles_df.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    ).dt.tz_convert(None)

    df["symbol"] = df["symbol"].map(
        normalize_symbol
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="raise",
        )

    calculated_parts = []

    for _, symbol_df in df.groupby(
        "symbol",
        sort=False,
    ):
        calculated_parts.append(
            calculate_symbol_features(symbol_df)
        )

    result = pd.concat(
        calculated_parts,
        ignore_index=True,
    )

    result = result.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    return result


def build_inference_features(
    candles: list[dict],
    symbol: str,
    strategy_name: str,
) -> pd.DataFrame:
    if len(candles) < MIN_CANDLES:
        raise ValueError(
            f"at least {MIN_CANDLES} candles are required"
        )

    candles_df = pd.DataFrame(candles)

    candles_df["symbol"] = normalize_symbol(
        symbol
    )

    features_df = calculate_features(
        candles_df
    )

    features_df["strategy_name"] = strategy_name

    valid_rows = features_df.dropna(
        subset=FEATURE_COLUMNS
    )

    if valid_rows.empty:
        raise ValueError(
            "could not calculate a complete feature row"
        )

    result = valid_rows.iloc[[-1]][
        FEATURE_COLUMNS
    ].copy()

    for column in CAT_FEATURES:
        result[column] = result[column].astype(str)

    return result
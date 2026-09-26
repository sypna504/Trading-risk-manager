import pandas as pd
import numpy as np


def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()

    return (
        (series - rolling_mean)
        / rolling_std.replace(0, np.nan)
    )

def calculate_symbol_features(symbol_df: pd.DataFrame) -> pd.DataFrame:
    df = symbol_df.sort_values("timestamp").copy()

    close = df["close"]
    volume = df["volume"]

    df["volume_z_20"] = rolling_zscore(
        volume,
        20,
    )

    df["price_z_20"] = rolling_zscore(
        close,
        20,
    )

    df["high_20"] = (
        df["high"]
        .rolling(20)
        .max()
        .shift(1)
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
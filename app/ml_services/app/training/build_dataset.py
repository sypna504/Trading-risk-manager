from pathlib import Path

import pandas as pd

from ..features_builder import (
    FEATURE_COLUMNS,
    calculate_features,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RAW_DATA_PATH = DATA_DIR / "history_data.parquet"
OUTPUT_PATH = DATA_DIR / "ml_dataset_v2.parquet"


def build_dataset() -> pd.DataFrame:
    raw_df = pd.read_parquet(
        RAW_DATA_PATH
    )

    df = calculate_features(raw_df)

    horizon = 3
    fee = 0.001

    grouped = df.groupby(
        "symbol",
        group_keys=False,
    )

    df["entry_price"] = (
        grouped["open"]
        .shift(-1)
    )

    df["exit_price"] = (
        grouped["close"]
        .shift(-horizon)
    )

    future_lows = [
        grouped["low"].shift(-step)
        for step in range(1, horizon + 1)
    ]

    df["future_min_low"] = pd.concat(
        future_lows,
        axis=1,
    ).min(axis=1)

    df["net_return"] = (
        df["exit_price"]
        / df["entry_price"]
        - 1
        - 2 * fee
    )

    df["max_drawdown"] = (
        df["future_min_low"]
        / df["entry_price"]
        - 1
    )

    df["target_good_trade"] = (
        (df["net_return"] > 0.002)
        & (df["max_drawdown"] > -0.015)
    ).astype(int)

    breakout = df[
        df["signal_breakout"] == 1
    ].copy()

    breakout["strategy_name"] = "breakout"

    mean_reversion = df[
        df["signal_mean_reversion"] == 1
    ].copy()

    mean_reversion[
        "strategy_name"
    ] = "mean_reversion"

    dataset = pd.concat(
        [
            breakout,
            mean_reversion,
        ],
        ignore_index=True,
    )

    result_columns = [
        "timestamp",
        "entry_price",
        "exit_price",
        "net_return",
        "max_drawdown",
        "target_good_trade",
        *FEATURE_COLUMNS,
    ]

    dataset = dataset[result_columns]

    dataset = dataset.dropna(
        subset=[
            "entry_price",
            "exit_price",
            "net_return",
            "max_drawdown",
            *FEATURE_COLUMNS,
        ]
    )

    dataset = dataset[
        (dataset["entry_price"] > 0)
        & (dataset["exit_price"] > 0)
    ]

    dataset = dataset.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    dataset.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"saved dataset: {OUTPUT_PATH}"
    )
    print(
        f"rows: {len(dataset)}"
    )

    return dataset


if __name__ == "__main__":
    build_dataset()
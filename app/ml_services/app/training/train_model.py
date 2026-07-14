import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from catboost import Pool

from ..features_builder import (
    CAT_FEATURES,
    FEATURE_COLUMNS,
)


BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent

DATASET_PATH = (
    BASE_DIR
    / "data"
    / "ml_dataset_v2.parquet"
)

MODEL_PATH = (
    APP_DIR
    / "models"
    / "risk_model_v2_online.cbm"
)

CONFIG_PATH = (
    APP_DIR
    / "models"
    / "risk_model_v2_online_config.json"
)


def train_model() -> None:
    df = pd.read_parquet(
        DATASET_PATH
    )

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    for column in CAT_FEATURES:
        df[column] = df[column].astype(str)

    row_count = len(df)

    train_end = int(row_count * 0.70)
    validation_end = int(row_count * 0.85)

    train = df.iloc[:train_end].copy()

    validation = df.iloc[
        train_end:validation_end
    ].copy()

    test = df.iloc[
        validation_end:
    ].copy()

    train_pool = Pool(
        data=train[FEATURE_COLUMNS],
        label=train["target_good_trade"],
        cat_features=CAT_FEATURES,
    )

    validation_pool = Pool(
        data=validation[FEATURE_COLUMNS],
        label=validation["target_good_trade"],
        cat_features=CAT_FEATURES,
    )

    model = CatBoostClassifier(
        iterations=500,
        learning_rate=0.04,
        depth=5,
        loss_function="Logloss",
        eval_metric="AUC",
        random_seed=42,
        verbose=100,
    )

    model.fit(
        train_pool,
        eval_set=validation_pool,
        early_stopping_rounds=50,
        use_best_model=True,
    )

    validation_result = validation.copy()

    validation_result[
        "prob_good_trade"
    ] = model.predict_proba(
        validation_pool
    )[:, 1]

    threshold_rows = []

    for threshold in np.arange(
        0.30,
        0.71,
        0.01,
    ):
        selected = validation_result[
            validation_result[
                "prob_good_trade"
            ] >= threshold
        ]

        if len(selected) < 100:
            continue

        threshold_rows.append(
            {
                "threshold": float(threshold),
                "trades": len(selected),
                "mean_return": float(
                    selected["net_return"].mean()
                ),
                "total_return": float(
                    selected["net_return"].sum()
                ),
            }
        )

    if not threshold_rows:
        best_threshold = 0.5
    else:
        threshold_table = pd.DataFrame(
            threshold_rows
        )

        best_threshold = float(
            threshold_table
            .sort_values(
                "total_return",
                ascending=False,
            )
            .iloc[0]["threshold"]
        )

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model.save_model(
        MODEL_PATH
    )

    config = {
        "model_version": "risk_model_v2_online",
        "threshold": best_threshold,
        "feature_cols": FEATURE_COLUMNS,
        "cat_features": CAT_FEATURES,
        "train_start": str(
            train["timestamp"].min()
        ),
        "train_end": str(
            train["timestamp"].max()
        ),
    }

    CONFIG_PATH.write_text(
        json.dumps(
            config,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    print(
        f"saved model: {MODEL_PATH}"
    )
    print(
        f"saved config: {CONFIG_PATH}"
    )
    print(
        f"threshold: {best_threshold}"
    )


if __name__ == "__main__":
    train_model()
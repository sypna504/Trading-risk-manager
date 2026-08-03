from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from .build_dataset import build_dataset
from .evaluate_model import evaluate_predictions
from .time_split import walk_forward_time_splits
from .train_model import _fit_catboost, _pool, select_threshold
from .training_config import TrainingConfig


def _exclude_final_holdout(dataset: pd.DataFrame, test_ratio: float) -> pd.DataFrame:
    timestamps = pd.Index(pd.to_datetime(dataset["timestamp"]).drop_duplicates().sort_values())
    cutoff_index = max(int(len(timestamps) * (1.0 - test_ratio)), 1)
    allowed = timestamps[:cutoff_index]
    return dataset[dataset["timestamp"].isin(allowed)].copy()


def compare_training_windows(
    history: pd.DataFrame,
    config: TrainingConfig,
) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    parameters = config.model_search_space[1]

    for days in sorted(set(config.training_window_candidates)):
        local_config = replace(
            config,
            training_window_days=days,
            auto_select_training_window=False,
        )
        try:
            dataset = build_dataset(local_config, raw_df=history, save=False)
            comparison_data = _exclude_final_holdout(dataset, config.test_ratio)
            folds = walk_forward_time_splits(
                comparison_data,
                folds=min(config.walk_forward_folds, 3),
                minimum_fold_rows=config.minimum_fold_rows,
                purge_bars=config.purge_bars,
            )
            fold_reports = []
            for fold_id, (train, validation, test) in enumerate(folds):
                if (
                    train["target_good_trade"].nunique() < 2
                    or validation["target_good_trade"].nunique() < 2
                ):
                    continue
                model = _fit_catboost(train, validation, parameters, config)
                validation_probabilities = model.predict_proba(
                    _pool(validation, with_label=False)
                )[:, 1]
                threshold, _ = select_threshold(
                    validation, validation_probabilities, config
                )
                test_probabilities = model.predict_proba(
                    _pool(test, with_label=False)
                )[:, 1]
                metrics = evaluate_predictions(test, test_probabilities, threshold)
                fold_reports.append(
                    {
                        "fold": fold_id,
                        "threshold": threshold,
                        "metrics": metrics,
                    }
                )

            total_returns = [
                float(item["metrics"]["trading"].get("total_net_return") or 0.0)
                for item in fold_reports
            ]
            positive_rate = (
                float(np.mean([value > 0 for value in total_returns]))
                if total_returns
                else 0.0
            )
            reports.append(
                {
                    "training_window_days": days,
                    "dataset_rows": len(dataset),
                    "completed_folds": len(fold_reports),
                    "positive_return_fold_rate": positive_rate,
                    "median_total_net_return": (
                        float(np.median(total_returns)) if total_returns else None
                    ),
                    "sum_total_net_return": float(np.sum(total_returns)),
                    "folds": fold_reports,
                    "error": None,
                }
            )
        except Exception as error:
            reports.append(
                {
                    "training_window_days": days,
                    "completed_folds": 0,
                    "error": str(error),
                }
            )

    valid = [item for item in reports if item.get("completed_folds", 0) > 0]
    if not valid:
        return {
            "selected_training_window_days": config.training_window_days,
            "selection_reason": "no candidate window completed evaluation",
            "windows": reports,
        }

    best = max(
        valid,
        key=lambda item: (
            item["positive_return_fold_rate"],
            item["median_total_net_return"] or -float("inf"),
            item["sum_total_net_return"],
        ),
    )
    return {
        "selected_training_window_days": best["training_window_days"],
        "selection_reason": "best pre-test walk-forward stability",
        "windows": reports,
    }

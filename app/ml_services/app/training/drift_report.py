from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


def _psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float | None:
    ref = pd.to_numeric(reference, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    cur = pd.to_numeric(current, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if ref.empty or cur.empty or ref.nunique() < 2:
        return None
    boundaries = np.unique(ref.quantile(np.linspace(0, 1, bins + 1)).to_numpy())
    if len(boundaries) < 3:
        return None
    boundaries[0] = -np.inf
    boundaries[-1] = np.inf
    ref_counts = pd.cut(ref, boundaries, include_lowest=True).value_counts(sort=False)
    cur_counts = pd.cut(cur, boundaries, include_lowest=True).value_counts(sort=False)
    ref_rate = (ref_counts / ref_counts.sum()).clip(lower=1e-6)
    cur_rate = (cur_counts / cur_counts.sum()).clip(lower=1e-6)
    return float(((cur_rate - ref_rate) * np.log(cur_rate / ref_rate)).sum())


def build_drift_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    feature_columns: list[str],
    model_train_end: str | None = None,
    probability_column: str | None = None,
) -> dict[str, Any]:
    numeric_features = [
        column
        for column in feature_columns
        if column in reference.columns
        and column in current.columns
        and pd.api.types.is_numeric_dtype(reference[column])
    ]
    features: dict[str, Any] = {}
    for column in numeric_features:
        ref = pd.to_numeric(reference[column], errors="coerce").dropna()
        cur = pd.to_numeric(current[column], errors="coerce").dropna()
        if ref.empty or cur.empty:
            continue
        ks = ks_2samp(ref, cur)
        features[column] = {
            "reference_mean": float(ref.mean()),
            "current_mean": float(cur.mean()),
            "reference_std": float(ref.std()) if len(ref) > 1 else 0.0,
            "current_std": float(cur.std()) if len(cur) > 1 else 0.0,
            "psi": _psi(ref, cur),
            "ks_statistic": float(ks.statistic),
            "ks_pvalue": float(ks.pvalue),
        }

    latest_timestamp = None
    if "timestamp" in current.columns and not current.empty:
        latest_timestamp = pd.to_datetime(current["timestamp"], utc=True).max()
    train_end = pd.to_datetime(model_train_end, utc=True) if model_train_end else None
    now = pd.Timestamp.now(tz="UTC")

    report: dict[str, Any] = {
        "features": features,
        "reference_rows": int(len(reference)),
        "current_rows": int(len(current)),
        "last_data_timestamp": latest_timestamp.isoformat() if latest_timestamp is not None else None,
        "model_train_end": train_end.isoformat() if train_end is not None else None,
        "model_age_hours": float((now - train_end).total_seconds() / 3600) if train_end is not None else None,
        "data_lag_hours": float((now - latest_timestamp).total_seconds() / 3600) if latest_timestamp is not None else None,
    }
    report["stale_model"] = bool(
        report["model_age_hours"] is not None and report["model_age_hours"] > 72
    )
    if "target_good_trade" in reference.columns and "target_good_trade" in current.columns:
        report["positive_class_rate"] = {
            "reference": float(reference["target_good_trade"].mean()),
            "current": float(current["target_good_trade"].mean()),
        }
    if probability_column and probability_column in current.columns:
        probabilities = pd.to_numeric(current[probability_column], errors="coerce").dropna()
        report["probabilities"] = {
            "mean": float(probabilities.mean()) if len(probabilities) else None,
            "std": float(probabilities.std()) if len(probabilities) > 1 else 0.0,
            "unique_count": int(probabilities.nunique()),
        }
    return report

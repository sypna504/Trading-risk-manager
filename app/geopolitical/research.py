from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from .features import geopolitical_features
from .models import GeopoliticalEvent


def compare_geopolitical_features(
    market: pd.DataFrame,
    events: list[GeopoliticalEvent],
    *,
    base_features: list[str],
    target: str = "target_good_trade",
) -> dict[str, object]:
    frame = market.copy().sort_values("timestamp").reset_index(drop=True)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    feature_rows = [geopolitical_features(events, ts.to_pydatetime()) for ts in frame["timestamp"]]
    geo = pd.DataFrame(feature_rows, index=frame.index)
    frame = pd.concat([frame, geo], axis=1)
    geo_columns = list(geo.columns)

    split = max(10, int(len(frame) * 0.7))
    train, test = frame.iloc[:split], frame.iloc[split:]
    if len(test) < 5:
        raise ValueError("not enough OOS rows")

    def fit(columns: list[str]) -> dict[str, float | int | None]:
        x_train = train[columns].astype(float).fillna(0.0)
        x_test = test[columns].astype(float).fillna(0.0)
        y_train = train[target].astype(int)
        y_test = test[target].astype(int)
        model = LogisticRegression(max_iter=1000, random_state=42).fit(x_train, y_train)
        probability = model.predict_proba(x_test)[:, 1]
        auc = float(roc_auc_score(y_test, probability)) if y_test.nunique() > 1 else None
        pr = float(average_precision_score(y_test, probability)) if y_test.nunique() > 1 else None
        return {
            "roc_auc": auc,
            "pr_auc": pr,
            "brier": float(brier_score_loss(y_test, probability)),
            "log_loss": float(log_loss(y_test, np.clip(probability, 1e-8, 1-1e-8), labels=[0, 1])),
            "rows": int(len(test)),
        }

    baseline = fit(base_features)
    with_geo = fit([*base_features, *geo_columns])
    improvement = (
        baseline["brier"] - with_geo["brier"]
        if baseline["brier"] is not None and with_geo["brier"] is not None else None
    )
    return {
        "baseline": baseline,
        "with_geopolitical": with_geo,
        "brier_improvement": improvement,
        "geopolitical_improvement_proven": False,
        "production_gate_change": False,
        "note": "A single split is diagnostic only; real OOS/walk-forward evidence is required.",
    }

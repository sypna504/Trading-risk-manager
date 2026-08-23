from __future__ import annotations

import numpy as np
import pandas as pd

from app.training.prediction_sensitivity import build_sensitivity_report


class FakeModel:
    def predict_proba(self, pool):
        frame = pool.get_features()
        values = 1 / (1 + np.exp(-frame[:, 0]))
        return np.column_stack([1 - values, values])


def test_sensitivity_report_has_required_sections():
    frame = pd.DataFrame(
        {
            "rsi_14": [20.0, 40.0, 60.0],
            "atr_14_pct": [0.01, 0.02, 0.03],
            "ret_1": [-0.01, 0.0, 0.01],
            "volume_z_20": [-1.0, 0.0, 1.0],
            "ema_distance_20": [-0.01, 0.0, 0.01],
            "symbol": ["BTCUSDT"] * 3,
            "strategy_name": ["breakout"] * 3,
            "interval": ["1h"] * 3,
        }
    )

    class DataFrameModel:
        def predict_proba(self, pool):
            count = pool.num_row()
            values = np.linspace(0.2, 0.8, count)
            return np.column_stack([1 - values, values])

    report = build_sensitivity_report(
        DataFrameModel(),
        None,
        frame,
        ["symbol", "strategy_name", "interval"],
        ["BTCUSDT", "ETHUSDT"],
        ["breakout", "mean_reversion"],
        ["1h"],
    )
    assert "symbol" in report
    assert "strategy" in report
    assert "interval" in report
    assert "numerical" in report
    assert report["raw_probability_std"] > 0

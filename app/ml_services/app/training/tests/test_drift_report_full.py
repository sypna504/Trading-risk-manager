from __future__ import annotations

import numpy as np
import pandas as pd

from app.training.drift_report import _psi, build_drift_report


def test_psi_handles_invalid_and_shifted_distributions():
    assert _psi(pd.Series([], dtype=float), pd.Series([1.0])) is None
    assert _psi(pd.Series([1.0, 1.0]), pd.Series([1.0, 2.0])) is None
    value = _psi(pd.Series(range(100)), pd.Series(range(50, 150)))
    assert value is not None
    assert value >= 0


def test_build_drift_report_all_sections():
    reference = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=20, freq="h", tz="UTC"),
            "feature": np.arange(20, dtype=float),
            "target_good_trade": [0, 1] * 10,
        }
    )
    current = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-02", periods=20, freq="h", tz="UTC"),
            "feature": np.arange(20, 40, dtype=float),
            "target_good_trade": [1, 1, 0, 1] * 5,
            "prob": np.linspace(0.1, 0.9, 20),
        }
    )
    result = build_drift_report(
        reference,
        current,
        ["feature", "missing"],
        model_train_end="2026-01-01T00:00:00Z",
        probability_column="prob",
    )
    assert "feature" in result["features"]
    assert result["positive_class_rate"]["current"] == 0.75
    assert result["probabilities"]["unique_count"] == 20
    assert result["last_data_timestamp"] is not None


def test_build_drift_report_empty_frames():
    result = build_drift_report(pd.DataFrame(), pd.DataFrame(), ["x"])
    assert result["features"] == {}
    assert result["last_data_timestamp"] is None
    assert result["stale_model"] is False

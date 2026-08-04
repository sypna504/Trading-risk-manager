from types import SimpleNamespace

import pytest

from app.backend.api.app.routers import trade_decision_router as router


def _prediction(probability, version="v1"):
    return SimpleNamespace(
        prob_good_trade=probability,
        risk_score=1 - probability,
        threshold=0.5,
        trade_allowed=probability >= 0.5,
        risk_level="medium",
        model_version=version,
    )


def test_equal_probabilities_have_deterministic_breakout_tie_break():
    selected, _ = router._select_best_prediction(
        [
            ("mean_reversion", _prediction(0.7)),
            ("breakout", _prediction(0.7)),
        ]
    )
    assert selected == "breakout"


def test_one_failed_strategy_does_not_discard_successful_prediction(monkeypatch):
    def predict_quality(*, strategy_name, **_kwargs):
        if strategy_name == "breakout":
            raise ConnectionError("temporary failure")
        return _prediction(0.65)

    monkeypatch.setattr(router.trade_ml_client, "predict_quality", predict_quality)
    predictions, failures = router._get_strategy_predictions(
        active_strategies=["breakout", "mean_reversion"],
        symbol="BTCUSDT",
        interval="1h",
        candles=[object()] * 60,
    )
    assert predictions[0][0] == "mean_reversion"
    assert "breakout" in failures


def test_mixed_model_versions_are_rejected(monkeypatch):
    def predict_quality(*, strategy_name, **_kwargs):
        return _prediction(0.6, version=strategy_name)

    monkeypatch.setattr(router.trade_ml_client, "predict_quality", predict_quality)
    with pytest.raises(ConnectionError, match="model changed"):
        router._get_strategy_predictions(
            active_strategies=["breakout", "mean_reversion"],
            symbol="BTCUSDT",
            interval="1h",
            candles=[object()] * 60,
        )

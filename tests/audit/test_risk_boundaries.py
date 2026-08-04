import pytest

from app.backend.api.app.services.risk_service import calculate_risk_parameters


def _calculate(**overrides):
    values = {
        "account_balance": 1000,
        "risk_per_trade_pct": 1,
        "max_position_share_pct": 25,
        "entry_price": 100,
        "atr_14_pct": 0.02,
        "probability": 0.7,
        "threshold": 0.6,
        "model_trade_allowed": True,
        "signal_detected": True,
    }
    values.update(overrides)
    return calculate_risk_parameters(**values)


def test_inconsistent_model_flag_does_not_open_position():
    result = _calculate(probability=0.4, threshold=0.6, model_trade_allowed=True)
    assert result["recommended_position_size"] == 0


def test_extreme_atr_cannot_create_negative_stop_loss():
    with pytest.raises(ValueError, match="below 100%"):
        _calculate(atr_14_pct=1.0)


def test_non_finite_balance_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        _calculate(account_balance=float("nan"))

from app.backend.api.app.services.risk_service import calculate_risk_parameters


def test_position_notional_does_not_exceed_cap():
    result = calculate_risk_parameters(
        account_balance=1000,
        risk_per_trade_pct=2,
        max_position_share_pct=10,
        entry_price=100,
        atr_14_pct=0.01,
        probability=0.7,
        threshold=0.5,
        model_trade_allowed=True,
    )

    assert result["recommended_position_notional"] <= 100
    assert result["risk_reward_ratio"] >= 2


def test_disallowed_trade_has_zero_position():
    result = calculate_risk_parameters(
        account_balance=1000,
        risk_per_trade_pct=1,
        max_position_share_pct=25,
        entry_price=100,
        atr_14_pct=0.01,
        probability=0.45,
        threshold=0.5,
        model_trade_allowed=False,
    )

    assert result["recommended_position_size"] == 0
    assert result["recommended_position_notional"] == 0

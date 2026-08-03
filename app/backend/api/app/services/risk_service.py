from __future__ import annotations

from typing import Any

from ..config import settings


def calculate_risk_parameters(
    *,
    account_balance: float,
    risk_per_trade_pct: float,
    max_position_share_pct: float,
    entry_price: float,
    atr_14_pct: float,
    probability: float,
    threshold: float,
    model_trade_allowed: bool,
    signal_detected: bool = True,
) -> dict[str, Any]:
    if account_balance <= 0:
        raise ValueError("account_balance must be greater than zero")
    if not 0 < risk_per_trade_pct <= 10:
        raise ValueError("risk_per_trade_pct must be between 0 and 10")
    if not 1 <= max_position_share_pct <= 100:
        raise ValueError(
            "max_position_share_pct must be between 1 and 100"
        )
    if entry_price <= 0:
        raise ValueError("entry_price must be greater than zero")
    if atr_14_pct <= 0:
        raise ValueError("atr_14_pct must be greater than zero")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    risk_amount = account_balance * risk_per_trade_pct / 100
    min_stop_fraction = settings.MIN_STOP_LOSS_PCT / 100
    stop_loss_fraction = max(
        atr_14_pct * settings.ATR_STOP_MULTIPLIER,
        min_stop_fraction,
    )
    take_profit_fraction = (
        stop_loss_fraction * settings.RISK_REWARD_RATIO
    )

    stop_loss_price = entry_price * (1 - stop_loss_fraction)
    take_profit_price = entry_price * (1 + take_profit_fraction)

    allowed = signal_detected and model_trade_allowed

    raw_position_size = risk_amount / (
        entry_price * stop_loss_fraction
    )
    raw_notional = raw_position_size * entry_price
    maximum_notional = (
        account_balance * max_position_share_pct / 100
    )
    recommended_notional = min(raw_notional, maximum_notional)
    recommended_size = recommended_notional / entry_price

    if not allowed:
        recommended_notional = 0.0
        recommended_size = 0.0

    position_share_pct = (
        recommended_notional / account_balance * 100
        if account_balance
        else 0.0
    )

    reason = (
        "position calculated from account risk, ATR stop and notional cap"
        if allowed
        else "position size is zero because the signal or model is not allowed"
    )

    return {
        "risk_amount": round(risk_amount, 8),
        "recommended_position_size": round(recommended_size, 8),
        "recommended_position_notional": round(
            recommended_notional,
            8,
        ),
        "position_share_pct": round(position_share_pct, 6),
        "entry_price": round(entry_price, 8),
        "stop_loss_price": round(stop_loss_price, 8),
        "take_profit_price": round(take_profit_price, 8),
        "stop_loss_pct": round(stop_loss_fraction * 100, 6),
        "take_profit_pct": round(take_profit_fraction * 100, 6),
        "risk_reward_ratio": settings.RISK_REWARD_RATIO,
        "side": "long",
        "calculation_reason": reason,
    }

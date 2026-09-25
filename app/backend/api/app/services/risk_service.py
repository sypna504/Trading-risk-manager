from __future__ import annotations

import math
from typing import Any

from ..config import settings


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


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
    atr_stop_multiplier: float | None = None,
    min_stop_loss_pct: float | None = None,
    risk_reward_ratio: float | None = None,
) -> dict[str, Any]:
    account_balance = _finite("account_balance", account_balance)
    risk_per_trade_pct = _finite("risk_per_trade_pct", risk_per_trade_pct)
    max_position_share_pct = _finite("max_position_share_pct", max_position_share_pct)
    entry_price = _finite("entry_price", entry_price)
    atr_14_pct = _finite("atr_14_pct", atr_14_pct)
    probability = _finite("probability", probability)
    threshold = _finite("threshold", threshold)

    if account_balance <= 0:
        raise ValueError("account_balance must be greater than zero")
    if not 0 < risk_per_trade_pct <= 10:
        raise ValueError("risk_per_trade_pct must be between 0 and 10")
    if not 1 <= max_position_share_pct <= 100:
        raise ValueError("max_position_share_pct must be between 1 and 100")
    if entry_price <= 0:
        raise ValueError("entry_price must be greater than zero")
    if atr_14_pct <= 0:
        raise ValueError("atr_14_pct must be greater than zero")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    atr_stop_multiplier = _finite(
        "atr_stop_multiplier",
        settings.ATR_STOP_MULTIPLIER
        if atr_stop_multiplier is None
        else atr_stop_multiplier,
    )
    min_stop_loss_pct = _finite(
        "min_stop_loss_pct",
        settings.MIN_STOP_LOSS_PCT
        if min_stop_loss_pct is None
        else min_stop_loss_pct,
    )
    risk_reward_ratio = _finite(
        "risk_reward_ratio",
        settings.RISK_REWARD_RATIO
        if risk_reward_ratio is None
        else risk_reward_ratio,
    )
    if atr_stop_multiplier <= 0:
        raise ValueError("atr_stop_multiplier must be greater than zero")
    if not 0 < min_stop_loss_pct < 100:
        raise ValueError("min_stop_loss_pct must be between 0 and 100")
    if risk_reward_ratio < 1:
        raise ValueError("risk_reward_ratio must be at least 1")

    risk_amount = account_balance * risk_per_trade_pct / 100
    min_stop_fraction = min_stop_loss_pct / 100
    stop_loss_fraction = max(
        atr_14_pct * atr_stop_multiplier,
        min_stop_fraction,
    )
    if stop_loss_fraction >= 1:
        raise ValueError(
            "calculated stop-loss distance must be below 100% of entry price"
        )

    take_profit_fraction = stop_loss_fraction * risk_reward_ratio
    stop_loss_price = entry_price * (1 - stop_loss_fraction)
    take_profit_price = entry_price * (1 + take_profit_fraction)

    allowed = (
        signal_detected
        and bool(model_trade_allowed)
        and probability >= threshold
    )

    raw_position_size = risk_amount / (entry_price * stop_loss_fraction)
    raw_notional = raw_position_size * entry_price
    maximum_notional = account_balance * max_position_share_pct / 100
    recommended_notional = min(raw_notional, maximum_notional)
    recommended_size = recommended_notional / entry_price

    if not allowed:
        recommended_notional = 0.0
        recommended_size = 0.0

    position_share_pct = recommended_notional / account_balance * 100
    reason = (
        "position calculated from account risk and the model target ATR/RR contract"
        if allowed
        else "position size is zero because the signal or model is not allowed"
    )

    return {
        "risk_amount": round(risk_amount, 8),
        "recommended_position_size": round(recommended_size, 8),
        "recommended_position_notional": round(recommended_notional, 8),
        "position_share_pct": round(position_share_pct, 6),
        "entry_price": round(entry_price, 8),
        "stop_loss_price": round(stop_loss_price, 8),
        "take_profit_price": round(take_profit_price, 8),
        "stop_loss_pct": round(stop_loss_fraction * 100, 6),
        "take_profit_pct": round(take_profit_fraction * 100, 6),
        "risk_reward_ratio": risk_reward_ratio,
        "side": "long",
        "calculation_reason": reason,
    }

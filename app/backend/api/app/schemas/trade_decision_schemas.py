from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RiskParameters(BaseModel):
    risk_amount: float
    recommended_position_size: float
    recommended_position_notional: float
    position_share_pct: float
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    stop_loss_pct: float
    take_profit_pct: float
    risk_reward_ratio: float
    side: Literal["long"]
    calculation_reason: str


class TradeDecisionResponse(BaseModel):
    id: int | None = None
    status: Literal["no_signal", "evaluated"]
    signal_detected: bool
    trade_allowed: bool
    active_strategies: list[str]
    selected_strategy: str | None = None
    strategy_name: str | None = None
    reason: str
    exchange: str
    symbol: str
    interval: str
    candles_count: int
    checked_at: str
    entry_price: float | None = None
    prob_good_trade: float | None = Field(default=None, ge=0, le=1)
    risk_score: float | None = Field(default=None, ge=0, le=1)
    threshold: float | None = Field(default=None, ge=0, le=1)
    risk_level: str | None = None
    model_version: str | None = None
    risk_parameters: RiskParameters | None = None
    signal_timestamp: str | None = None
    outcome_due_at: str | None = None
    outcome_status: str | None = None


class StoredDecisionResponse(BaseModel):
    id: int
    created_at: str
    exchange: str
    symbol: str
    interval: str
    candles_count: int
    signal_detected: bool
    active_strategies: list[str]
    selected_strategy: str | None = None
    probability: float | None = None
    threshold: float | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    trade_allowed: bool
    model_version: str | None = None
    entry_price: float | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    position_size: float | None = None
    position_notional: float | None = None
    account_balance: float | None = None
    risk_per_trade_pct: float | None = None
    status: str
    reason: str
    signal_timestamp: str | None = None
    outcome_due_at: str | None = None
    outcome_status: str = "pending"
    outcome_checked_at: str | None = None
    realized_entry_price: float | None = None
    realized_exit_price: float | None = None
    realized_net_return: float | None = None
    realized_max_drawdown: float | None = None
    actual_target: bool | None = None
    prediction_correct: bool | None = None
    outcome_error: str | None = None
    target_horizon_bars: int = 3
    target_min_net_return: float = 0.002
    target_max_drawdown: float = -0.015


class OutcomeEvaluationResponse(BaseModel):
    checked: int
    completed: int
    retries: int
    errors: dict[int, str]


class OutcomeSummaryResponse(BaseModel):
    total: int
    completed: int
    pending: int
    correct: int
    incorrect: int
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    accuracy: float | None = None
    by_strategy: dict[str, dict]

from __future__ import annotations

from typing import Any, Literal

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
    active_strategies: list[str] = Field(default_factory=list)
    selected_strategy: str | None = None
    strategy_name: str | None = None
    reason: str
    exchange: str
    symbol: str
    interval: str
    candles_count: int
    checked_at: str

    # entry_price is kept as a compatibility alias for planned_entry_price.
    # It is not a realized fill.
    entry_price: float | None = None
    signal_close_price: float | None = None
    planned_entry_price: float | None = None
    realized_entry_price: float | None = None
    entry_convention: str | None = None

    prob_good_trade: float | None = Field(default=None, ge=0, le=1)
    raw_prob_good_trade: float | None = Field(default=None, ge=0, le=1)
    risk_score: float | None = Field(default=None, ge=0, le=1)
    threshold: float | None = Field(default=None, ge=0, le=1)
    risk_level: str | None = None
    model_version: str | None = None
    feature_schema_version: str | None = None
    model_status: str | None = None
    calibration_method: str | None = None
    model_warnings: list[str] = Field(default_factory=list)
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
    active_strategies: list[str] = Field(default_factory=list)
    selected_strategy: str | None = None
    probability: float | None = None
    raw_probability: float | None = None
    threshold: float | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    trade_allowed: bool
    model_version: str | None = None
    feature_schema_version: str | None = None
    model_status: str | None = None
    calibration_method: str | None = None
    market_regime: str | None = None
    entry_price: float | None = None
    signal_close_price: float | None = None
    planned_entry_price: float | None = None
    entry_convention: str | None = None
    exit_convention: str | None = None
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
    outcome_attempts: int = 0
    outcome_checked_at: str | None = None
    realized_entry_price: float | None = None
    realized_exit_price: float | None = None
    realized_net_return: float | None = None
    realized_max_drawdown: float | None = None
    actual_target: bool | None = None
    prediction_correct: bool | None = None
    outcome_error: str | None = None
    target_definition: str = "horizon_return_drawdown"
    target_horizon_minutes: int = 180
    target_horizon_bars: int = 3
    target_min_net_return: float = 0.002
    target_max_drawdown: float = -0.015
    target_fee: float = 0.001
    target_slippage: float = 0.0005
    target_stop_loss_fraction: float | None = None
    target_risk_reward_ratio: float | None = None
    target_intrabar_priority: str | None = None
    realized_exit_reason: str | None = None
    realized_holding_bars: int | None = None


class OutcomeEvaluationResponse(BaseModel):
    checked: int
    completed: int
    retries: int
    invalid_data: int = 0
    errors: dict[int, str] = Field(default_factory=dict)


class OutcomeSummaryResponse(BaseModel):
    total: int
    completed: int
    pending: int
    invalid_data: int = 0
    correct: int
    incorrect: int
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: float | None = None
    recall: float | None = None
    specificity: float | None = None
    false_positive_rate: float | None = None
    false_negative_rate: float | None = None
    accuracy: float | None = None
    brier_score: float | None = None
    mean_realized_net_return: float | None = None
    total_realized_net_return: float = 0.0
    missed_good_trades: int = 0
    bad_allowed_trades: int = 0
    calibration_bins: list[dict[str, Any]] = Field(default_factory=list)
    by_symbol: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_strategy: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_interval: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_model_version: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_market_regime: dict[str, dict[str, Any]] = Field(default_factory=dict)
    rolling_7d: dict[str, Any] = Field(default_factory=dict)
    rolling_30d: dict[str, Any] = Field(default_factory=dict)

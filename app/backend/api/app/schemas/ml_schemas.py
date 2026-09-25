from __future__ import annotations

from pydantic import BaseModel, Field

from ..config import settings


class MLpredictresponse(BaseModel):
    exchange: str
    symbol: str
    interval: str
    strategy_name: str
    candles_count: int = Field(ge=settings.MIN_CANDLES)
    prob_good_trade: float = Field(ge=0, le=1)
    raw_prob_good_trade: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=1)
    trade_allowed: bool
    threshold: float = Field(ge=0, le=1)
    risk_level: str
    model_version: str
    feature_schema_version: str
    model_status: str
    calibration_method: str
    probability_bin: str
    model_supported_interval: str
    model_warnings: list[str] = Field(default_factory=list)


class ModelInfoResponse(BaseModel):
    model_version: str | None = None
    model_status: str | None = None
    threshold: float | None = None
    thresholds_by_strategy: dict[str, float] = Field(default_factory=dict)
    supported_intervals: list[str] = Field(default_factory=list)
    supported_strategies: list[str] = Field(default_factory=list)
    supported_symbols: list[str] = Field(default_factory=list)
    allow_unseen_symbols: bool = False
    supported_exchanges: list[str] = Field(default_factory=list)
    feature_schema_version: str | None = None
    target_horizon_minutes: int | None = None
    target_horizon_bars: int | None = None
    minimum_net_return: float | None = None
    maximum_target_drawdown: float | None = None
    fee: float | None = None
    slippage: float | None = None
    entry_convention: str | None = None
    exit_convention: str | None = None
    calibration_method: str | None = None
    train_start: str | None = None
    train_end: str | None = None
    evaluation_train_end: str | None = None
    evaluation_test_end: str | None = None
    production_train_end: str | None = None
    feature_count: int = 0
    feature_cols: list[str] = Field(default_factory=list)
    cat_features: list[str] = Field(default_factory=list)
    model_file_exists: bool
    config_file_exists: bool
    model_age_days: int | None = None
    data_age_hours: float | None = None
    is_model_stale: bool | None = None
    warnings: list[str] = Field(default_factory=list)

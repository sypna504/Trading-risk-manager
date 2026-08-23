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
    calibration_method: str
    probability_bin: str
    model_supported_interval: str


class ModelInfoResponse(BaseModel):
    model_version: str | None = None
    threshold: float | None = None
    thresholds_by_strategy: dict[str, float] = Field(default_factory=dict)
    supported_intervals: list[str] = Field(default_factory=list)
    supported_strategies: list[str] = Field(default_factory=list)
    feature_schema_version: str | None = None
    target_horizon_minutes: int | None = None
    train_start: str | None = None
    train_end: str | None = None
    feature_count: int = 0
    feature_cols: list[str] = Field(default_factory=list)
    cat_features: list[str] = Field(default_factory=list)
    model_file_exists: bool
    config_file_exists: bool
    model_age_days: int | None = None
    is_model_stale: bool | None = None

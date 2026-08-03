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
    risk_score: float = Field(ge=0, le=1)
    trade_allowed: bool
    threshold: float = Field(ge=0, le=1)
    risk_level: str
    model_version: str


class ModelInfoResponse(BaseModel):
    model_version: str | None = None
    threshold: float | None = None
    train_start: str | None = None
    train_end: str | None = None
    feature_count: int = 0
    feature_cols: list[str] = []
    cat_features: list[str] = []
    model_file_exists: bool
    config_file_exists: bool
    model_age_days: int | None = None
    is_model_stale: bool | None = None

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class PositionStatus(str, Enum):
    PENDING_ENTRY = "pending_entry"
    OPEN = "open"
    CLOSED = "closed"
    REJECTED = "rejected"


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TIMEOUT = "timeout"


class PaperRiskConfig(BaseModel):
    max_position_share_pct: float = Field(default=25.0, gt=0, le=100)
    max_risk_per_trade_pct: float = Field(default=2.0, gt=0, le=100)
    max_concurrent_positions: int = Field(default=5, ge=1, le=100)
    max_gross_exposure_pct: float = Field(default=80.0, gt=0, le=500)
    max_portfolio_risk_pct: float = Field(default=5.0, gt=0, le=100)
    default_fee: float = Field(default=0.001, ge=0, le=0.05)
    default_slippage: float = Field(default=0.0005, ge=0, le=0.05)
    intrabar_priority: str = "stop_loss"


class PaperPortfolio(BaseModel):
    portfolio_id: str = "default"
    starting_balance: float = 10_000.0
    current_equity: float = 10_000.0
    cash: float = 10_000.0
    gross_exposure: float = 0.0
    open_risk: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    peak_equity: float = 10_000.0
    max_drawdown: float = 0.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("updated_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class VirtualPosition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    exchange: str = "binance"
    interval: str = "1h"
    strategy: str
    model_version: str
    decision_id: int
    opened_at: datetime | None = None
    planned_entry: float
    realized_virtual_entry: float | None = None
    quantity: float = 0.0
    notional: float = 0.0
    stop_loss: float
    take_profit: float
    timeout_at: datetime
    fee: float
    slippage: float
    status: PositionStatus = PositionStatus.PENDING_ENTRY
    exit_at: datetime | None = None
    exit_price: float | None = None
    exit_reason: ExitReason | None = None
    realized_pnl: float | None = None
    return_pct: float | None = None
    risk_amount: float = 0.0
    news_snapshot: dict | None = None

    @field_validator("opened_at", "timeout_at", "exit_at")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

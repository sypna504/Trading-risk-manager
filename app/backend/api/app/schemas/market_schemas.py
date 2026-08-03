from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Exchanges(str, Enum):
    BYBIT = "bybit"
    BINANCE = "binance"


class Intervals(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class CandleItem(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class CandlesListResponce(BaseModel):
    exchange: Exchanges
    symbol: str
    interval: Intervals
    limit: int = Field(ge=1, le=5000)
    candles: list[CandleItem]

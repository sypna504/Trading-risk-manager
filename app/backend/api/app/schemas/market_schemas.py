from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum

class Exchanges(str, Enum):
    BYBIT = 'bybit'
    BINANCE = 'binance'

class Intervals(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class CandleItem(BaseModel):
    timestamp: int = Field(description="timestamp")
    open: float = Field(gt=0, description="open")
    high: float = Field(gt=0, description="high")
    low: float = Field(gt=0, description="low")
    close: float = Field(gt=0, description="close")
    volume: float = Field(ge=0, description="volume")


class CandlesListResponce(BaseModel):
    exchange: Exchanges
    symbol: str
    interval: Intervals
    limit : int=Field(ge=1, le=5000)
    candles: list
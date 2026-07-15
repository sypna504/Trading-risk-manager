from pydantic import BaseModel
from pydantic import Field
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
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Candle(_message.Message):
    __slots__ = ("timestamp_ms", "open", "high", "low", "close", "volume")
    TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    def __init__(self, timestamp_ms: _Optional[int] = ..., open: _Optional[float] = ..., high: _Optional[float] = ..., low: _Optional[float] = ..., close: _Optional[float] = ..., volume: _Optional[float] = ...) -> None: ...

class PredictSignalQualityRequest(_message.Message):
    __slots__ = ("symbol", "interval", "strategy_name", "candles")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    CANDLES_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    interval: str
    strategy_name: str
    candles: _containers.RepeatedCompositeFieldContainer[Candle]
    def __init__(self, symbol: _Optional[str] = ..., interval: _Optional[str] = ..., strategy_name: _Optional[str] = ..., candles: _Optional[_Iterable[_Union[Candle, _Mapping]]] = ...) -> None: ...

class PredictSignalQualityResponse(_message.Message):
    __slots__ = ("prob_good_trade", "risk_score", "trade_allowed", "threshold", "risk_level", "model_version")
    PROB_GOOD_TRADE_FIELD_NUMBER: _ClassVar[int]
    RISK_SCORE_FIELD_NUMBER: _ClassVar[int]
    TRADE_ALLOWED_FIELD_NUMBER: _ClassVar[int]
    THRESHOLD_FIELD_NUMBER: _ClassVar[int]
    RISK_LEVEL_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    prob_good_trade: float
    risk_score: float
    trade_allowed: bool
    threshold: float
    risk_level: str
    model_version: str
    def __init__(self, prob_good_trade: _Optional[float] = ..., risk_score: _Optional[float] = ..., trade_allowed: _Optional[bool] = ..., threshold: _Optional[float] = ..., risk_level: _Optional[str] = ..., model_version: _Optional[str] = ...) -> None: ...

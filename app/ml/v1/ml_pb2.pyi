from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SignalFeatures(_message.Message):
    __slots__ = ("rsi_14", "return_1", "return_6", "return_24", "volatility_24", "volume_zscore", "trend_strength", "ma_distance")
    RSI_14_FIELD_NUMBER: _ClassVar[int]
    RETURN_1_FIELD_NUMBER: _ClassVar[int]
    RETURN_6_FIELD_NUMBER: _ClassVar[int]
    RETURN_24_FIELD_NUMBER: _ClassVar[int]
    VOLATILITY_24_FIELD_NUMBER: _ClassVar[int]
    VOLUME_ZSCORE_FIELD_NUMBER: _ClassVar[int]
    TREND_STRENGTH_FIELD_NUMBER: _ClassVar[int]
    MA_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    rsi_14: float
    return_1: float
    return_6: float
    return_24: float
    volatility_24: float
    volume_zscore: float
    trend_strength: float
    ma_distance: float
    def __init__(self, rsi_14: _Optional[float] = ..., return_1: _Optional[float] = ..., return_6: _Optional[float] = ..., return_24: _Optional[float] = ..., volatility_24: _Optional[float] = ..., volume_zscore: _Optional[float] = ..., trend_strength: _Optional[float] = ..., ma_distance: _Optional[float] = ...) -> None: ...

class PredictSignalQualityRequest(_message.Message):
    __slots__ = ("symbol", "interval", "strategy", "action", "features")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    interval: str
    strategy: str
    action: str
    features: SignalFeatures
    def __init__(self, symbol: _Optional[str] = ..., interval: _Optional[str] = ..., strategy: _Optional[str] = ..., action: _Optional[str] = ..., features: _Optional[_Union[SignalFeatures, _Mapping]] = ...) -> None: ...

class PredictSignalQualityResponse(_message.Message):
    __slots__ = ("p_win", "expected_return_pct", "risk_level", "model_version")
    P_WIN_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_RETURN_PCT_FIELD_NUMBER: _ClassVar[int]
    RISK_LEVEL_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    p_win: float
    expected_return_pct: float
    risk_level: str
    model_version: str
    def __init__(self, p_win: _Optional[float] = ..., expected_return_pct: _Optional[float] = ..., risk_level: _Optional[str] = ..., model_version: _Optional[str] = ...) -> None: ...

from __future__ import annotations

from collections.abc import Sequence
from datetime import timezone

import grpc
from ml.v1 import ml_pb2
from ml.v1 import ml_pb2_grpc

from .config import settings
from .services.market_services import Candle


class MLGrpcClient:
    def __init__(
        self,
        address: str | None = None,
        ready_timeout: float | None = None,
    ) -> None:
        self.address = address or settings.ML_SERVICE_ADDRESS
        self.ready_timeout = ready_timeout or settings.REQUEST_TIMEOUT
        self.channel = grpc.insecure_channel(self.address)
        self.stub = ml_pb2_grpc.MLServiceStub(self.channel)

    def _wait_until_ready(self) -> None:
        try:
            grpc.channel_ready_future(self.channel).result(
                timeout=self.ready_timeout,
            )
        except grpc.FutureTimeoutError as error:
            raise ConnectionError(
                f"ML service is unavailable at {self.address}"
            ) from error

    def is_ready(self, timeout: float = 2.0) -> bool:
        try:
            grpc.channel_ready_future(self.channel).result(timeout=timeout)
            return True
        except grpc.FutureTimeoutError:
            return False

    @staticmethod
    def _to_proto_candle(candle: Candle) -> ml_pb2.Candle:
        timestamp = candle.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)
        return ml_pb2.Candle(
            timestamp_ms=int(timestamp.timestamp() * 1000),
            open=float(candle.open),
            high=float(candle.high),
            low=float(candle.low),
            close=float(candle.close),
            volume=float(candle.volume),
        )

    def predict_quality(
        self,
        symbol: str,
        interval: str,
        strategy_name: str,
        candles: Sequence[Candle],
        timeout: float | None = None,
    ):
        if len(candles) < settings.MIN_CANDLES:
            raise ValueError(
                "at least "
                f"{settings.MIN_CANDLES} candles are required, "
                f"received {len(candles)}"
            )

        self._wait_until_ready()
        request = ml_pb2.PredictSignalQualityRequest(
            symbol=symbol,
            interval=interval,
            strategy_name=strategy_name,
            candles=[self._to_proto_candle(candle) for candle in candles],
        )

        try:
            return self.stub.PredictSignalQuality(
                request,
                timeout=timeout or settings.REQUEST_TIMEOUT,
            )
        except grpc.RpcError as error:
            code = error.code()
            details = error.details() or "no details"
            if code == grpc.StatusCode.INVALID_ARGUMENT:
                raise ValueError(details) from error
            if code == grpc.StatusCode.FAILED_PRECONDITION:
                raise ConnectionError(f"ML model is not ready: {details}") from error
            raise ConnectionError(
                f"ML service request failed [{code.name}]: {details}"
            ) from error

    def close(self) -> None:
        self.channel.close()

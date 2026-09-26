from __future__ import annotations

from collections.abc import Sequence
from datetime import timezone

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc
from ml.v1 import ml_pb2, ml_pb2_grpc

from .config import settings
from .request_context import current_request_id
from .services.market_services import Candle


class MLModelUnavailableError(ConnectionError):
    """The ML process is reachable but no valid active model is ready."""


class MLUpstreamError(ConnectionError):
    """The gRPC service itself is unavailable or failed unexpectedly."""


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
        self.health_stub = health_pb2_grpc.HealthStub(self.channel)

    def _wait_until_ready(self) -> None:
        try:
            grpc.channel_ready_future(self.channel).result(timeout=self.ready_timeout)
        except grpc.FutureTimeoutError as error:
            raise MLUpstreamError(
                f"ML service is unavailable at {self.address}"
            ) from error

    def health_status(self, timeout: float = 2.0) -> str:
        try:
            response = self.health_stub.Check(
                health_pb2.HealthCheckRequest(service="ml.v1.MLService"),
                timeout=timeout,
            )
        except grpc.RpcError:
            return "unavailable"
        if response.status == health_pb2.HealthCheckResponse.SERVING:
            return "serving"
        if response.status == health_pb2.HealthCheckResponse.NOT_SERVING:
            return "not_serving"
        return "unknown"

    def is_ready(self, timeout: float = 2.0) -> bool:
        return self.health_status(timeout=timeout) == "serving"

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
                f"at least {settings.MIN_CANDLES} candles are required, "
                f"received {len(candles)}"
            )
        self._wait_until_ready()
        request = ml_pb2.PredictSignalQualityRequest(
            symbol=symbol,
            interval=interval,
            strategy_name=strategy_name,
            candles=[self._to_proto_candle(candle) for candle in candles],
        )
        request_id = current_request_id()
        metadata = (("x-request-id", request_id),) if request_id else None
        try:
            return self.stub.PredictSignalQuality(
                request,
                timeout=timeout or settings.REQUEST_TIMEOUT,
                metadata=metadata,
            )
        except grpc.RpcError as error:
            code = error.code()
            details = error.details() or "no details"
            if code == grpc.StatusCode.INVALID_ARGUMENT:
                raise ValueError(details) from error
            if code == grpc.StatusCode.FAILED_PRECONDITION:
                raise MLModelUnavailableError(details) from error
            raise MLUpstreamError(
                f"ML service request failed [{code.name}]: {details}"
            ) from error

    def close(self) -> None:
        self.channel.close()

from __future__ import annotations
import os
from collections.abc import Sequence
from datetime import timezone
import grpc
from ml.v1 import ml_pb2
from ml.v1 import ml_pb2_grpc
from .services.market_services import Candle

DEFAULT_ML_SERVICE_ADDRESS = os.getenv(
    "ML_SERVICE_ADDRESS",
    "ml_service:50051",
)


class MLGrpcClient:
    def __init__(self,address: str | None = None,ready_timeout: float = 5.0):
        
        self.address = (
            address
            or DEFAULT_ML_SERVICE_ADDRESS
        )

        self.ready_timeout = ready_timeout

        self.channel = grpc.insecure_channel(
            self.address
        )

        self.stub = ml_pb2_grpc.MLServiceStub(
            self.channel
        )

    def _wait_until_ready(self) -> None:
        try:
            grpc.channel_ready_future(
                self.channel
            ).result(
                timeout=self.ready_timeout
            )

        except grpc.FutureTimeoutError as error:
            raise ConnectionError(
                (
                    "ML service is unavailable at "
                    f"{self.address}"
                )
            ) from error

    @staticmethod
    def _to_proto_candle(candle: Candle) -> ml_pb2.Candle:
        timestamp = candle.timestamp

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )
        else:
            timestamp = timestamp.astimezone(
                timezone.utc
            )

        return ml_pb2.Candle(
            timestamp_ms=int(
                timestamp.timestamp() * 1000
            ),
            open=float(candle.open),
            high=float(candle.high),
            low=float(candle.low),
            close=float(candle.close),
            volume=float(candle.volume),
        )

    def predict_quality(self,symbol: str,interval: str,strategy_name: str,candles: Sequence[Candle],timeout: float = 15.0):
        if len(candles) < 60:
            raise ValueError(
                (
                    "at least 60 candles are "
                    f"required, received {len(candles)}"
                )
            )

        self._wait_until_ready()

        proto_candles = [
            self._to_proto_candle(candle)
            for candle in candles
        ]

        request = (
            ml_pb2.PredictSignalQualityRequest(
                symbol=symbol,
                interval=interval,
                strategy_name=strategy_name,
                candles=proto_candles,
            )
        )

        return self.stub.PredictSignalQuality(
            request,
            timeout=timeout,
        )

    def close(self) -> None:
        self.channel.close()
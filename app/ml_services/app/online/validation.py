from __future__ import annotations

import math

import grpc

from ..config import settings


ALLOWED_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}
ALLOWED_STRATEGIES = {"breakout", "mean_reversion"}


class Validator:
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def validate_symbol(self):
        if not self.request.symbol.strip():
            self.context.abort(grpc.StatusCode.INVALID_ARGUMENT, "symbol is required")

    def validate_interval(self):
        if self.request.interval not in ALLOWED_INTERVALS:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "interval must be one of: " + ", ".join(sorted(ALLOWED_INTERVALS)),
            )

    def validate_strategy(self):
        if self.request.strategy_name not in ALLOWED_STRATEGIES:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "strategy_name must be breakout or mean_reversion",
            )

    def validate_candles_count(self):
        candles_count = len(self.request.candles)
        if candles_count < settings.MIN_CANDLES:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"at least {settings.MIN_CANDLES} candles are required, "
                f"received {candles_count}",
            )

    def validate_candles(self):
        for index, candle in enumerate(self.request.candles):
            if candle.timestamp_ms <= 0:
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"invalid timestamp at candle {index}",
                )

            values = (
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
            )
            if not all(math.isfinite(value) for value in values):
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"OHLCV values must be finite at candle {index}",
                )
            if any(
                value <= 0
                for value in (
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                )
            ):
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"OHLC values must be positive at candle {index}",
                )
            if candle.volume < 0:
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"volume must be non-negative at candle {index}",
                )
            if candle.high < max(
                candle.open,
                candle.close,
                candle.low,
            ):
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"high is lower than another OHLC value at candle {index}",
                )
            if candle.low > min(
                candle.open,
                candle.close,
                candle.high,
            ):
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"low is higher than another OHLC value at candle {index}",
                )

    def validate_timestamp_order(self):
        timestamps = [candle.timestamp_ms for candle in self.request.candles]
        if timestamps != sorted(timestamps):
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "candles must be sorted by timestamp",
            )
        if len(timestamps) != len(set(timestamps)):
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "candles contain duplicate timestamps",
            )

    def validate(self):
        self.validate_symbol()
        self.validate_interval()
        self.validate_strategy()
        self.validate_candles_count()
        self.validate_candles()
        self.validate_timestamp_order()

import grpc

ALLOWED_INTERVALS = {
    "1m",
    "5m",
    "15m",
    "1h",
    "4h",
    "1d",
}

ALLOWED_STRATEGIES = {
    "breakout",
    "mean_reversion",
}

MIN_CANDLES = 60

class Validator:
    def __init__(self, context, request):
        self.context = context
        self.request = request
    
    def validate_symbol(self):
        if not self.request.symbol.strip():
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "symbol is required",
            )

    def validate_interval(self):
        if self.request.interval not in ALLOWED_INTERVALS:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                (
                    "interval must be one of: "
                    + ", ".join(sorted(ALLOWED_INTERVALS))
                ),
            )

    def validate_strategy(self):
        if (
            self.request.strategy_name
            not in ALLOWED_STRATEGIES
        ):
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                (
                    "strategy_name must be "
                    "breakout or mean_reversion"
                ),
            )
    def validate_candles_count(self):
        candles_count = len(self.request.candles)

        print(
            f"validator received candles: {candles_count}",
            flush=True,
        )

        if candles_count < MIN_CANDLES:
            self.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                (
                    f"at least {MIN_CANDLES} candles "
                    f"are required, received {candles_count}"
                ),
            )
    def validate_candles(self):
        for index, candle in enumerate(
            self.request.candles
        ):
            if candle.timestamp_ms <= 0:
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    (
                        "invalid timestamp at "
                        f"candle {index}"
                    ),
                )

            if (
                candle.open <= 0
                or candle.high <= 0
                or candle.low <= 0
                or candle.close <= 0
            ):
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    (
                        "OHLC values must be "
                        f"positive at candle {index}"
                    ),
                )

            if candle.volume < 0:
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    (
                        "volume must be non-negative "
                        f"at candle {index}"
                    ),
                )

            if candle.high < max(
                candle.open,
                candle.close,
            ):
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    (
                        "high is lower than "
                        f"open or close at candle {index}"
                    ),
                )

            if candle.low > min(
                candle.open,
                candle.close,
            ):
                self.context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    (
                        "low is higher than "
                        f"open or close at candle {index}"
                    ),
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
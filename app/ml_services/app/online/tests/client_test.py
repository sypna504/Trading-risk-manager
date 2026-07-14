import math
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import grpc
from ml.v1 import ml_pb2
from ml.v1 import ml_pb2_grpc

GRPC_ADDRESS = "127.0.0.1:50051"


def generate_test_candles(
    count: int = 100,
) -> list:
    candles = []

    start_time = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    previous_close = 100.0

    for index in range(count):
        timestamp = (
            start_time
            + timedelta(hours=index)
        )

        price_change = (
            0.08
            + math.sin(index / 5) * 0.5
        )

        open_price = previous_close

        close_price = max(
            1.0,
            open_price + price_change,
        )

        high_price = (
            max(open_price, close_price)
            + 0.4
        )

        low_price = (
            min(open_price, close_price)
            - 0.4
        )

        volume = (
            1000
            + index * 5
            + math.sin(index / 3) * 100
        )

        candles.append(
            ml_pb2.Candle(
                timestamp_ms=int(
                    timestamp.timestamp() * 1000
                ),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )
        )

        previous_close = close_price

    return candles


def main() -> None:
    channel = grpc.insecure_channel(
        GRPC_ADDRESS
    )

    client = ml_pb2_grpc.MLServiceStub(
        channel
    )

    candles = generate_test_candles(
        count=100
    )
    print(
        "generated candles:",
        len(candles),
    )

    request = ml_pb2.PredictSignalQualityRequest(
        symbol="BTCUSDT",
        interval="1h",
        strategy_name="mean_reversion",
        candles=candles,
    )
    print(
        "candles in request:",
        len(request.candles),
    )

    try:
        response = (
            client.PredictSignalQuality(
                request,
                timeout=15,
            )
        )

        print(
            "prob_good_trade:",
            response.prob_good_trade,
        )

        print(
            "risk_score:",
            response.risk_score,
        )

        print(
            "trade_allowed:",
            response.trade_allowed,
        )

        print(
            "threshold:",
            response.threshold,
        )

        print(
            "risk_level:",
            response.risk_level,
        )

        print(
            "model_version:",
            response.model_version,
        )

    except grpc.RpcError as error:
        print(
            "gRPC status:",
            error.code(),
        )

        print(
            "gRPC details:",
            error.details(),
        )

        raise

    finally:
        channel.close()


if __name__ == "__main__":
    main()
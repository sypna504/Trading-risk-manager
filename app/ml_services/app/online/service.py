import grpc
import pandas as pd
from ml.v1 import ml_pb2
from ml.v1 import ml_pb2_grpc
from ..features_builder import build_inference_features
from ..online.ml_inference import predictor
from ..online.validation import Validator

class MLService(ml_pb2_grpc.MLServiceServicer):
    def PredictSignalQuality(self, request, context):
        validator = Validator(context, request)
        validator.validate()
        print(
            f"server received candles: {len(request.candles)}",
            flush=True,
        )
        try:
            candles = []

            for candle in request.candles:
                timestamp = pd.to_datetime(
                    candle.timestamp_ms,
                    unit="ms",
                    utc=True,
                ).tz_convert(None)

                candles.append(
                    {
                        "timestamp": timestamp,
                        "open": candle.open,
                        "high": candle.high,
                        "low": candle.low,
                        "close": candle.close,
                        "volume": candle.volume,
                    }
                )

            features = build_inference_features(
                candles=candles,
                symbol=request.symbol,
                strategy_name=request.strategy_name,
            )

            prediction = predictor.predict(
                features
            )

            return ml_pb2.PredictSignalQualityResponse(
                    prob_good_trade=prediction[
                        "prob_good_trade"
                    ],
                    risk_score=prediction[
                        "risk_score"
                    ],
                    trade_allowed=prediction[
                        "trade_allowed"
                    ],
                    threshold=prediction[
                        "threshold"
                    ],
                    risk_level=prediction[
                        "risk_level"
                    ],
                    model_version=prediction[
                        "model_version"
                    ],
                )

        except ValueError as error:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                str(error),
            )

        except FileNotFoundError as error:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                str(error),
            )

        except Exception as error:
            context.abort(
                grpc.StatusCode.INTERNAL,
                f"prediction failed: {error}",
            )
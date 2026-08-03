from __future__ import annotations

import logging
import time

import grpc
import pandas as pd
from ml.v1 import ml_pb2, ml_pb2_grpc

from ..features_builder import build_inference_features
from .ml_inference import predictor
from .validation import Validator


logger = logging.getLogger(__name__)


class MLService(ml_pb2_grpc.MLServiceServicer):
    def PredictSignalQuality(self, request, context):
        started = time.perf_counter()
        validator = Validator(context, request)
        validator.validate()

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
            prediction = predictor.predict(features)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

            logger.info(
                "symbol=%s interval=%s strategy=%s model_version=%s "
                "candles=%s trade_allowed=%s elapsed_ms=%s",
                request.symbol,
                request.interval,
                request.strategy_name,
                prediction["model_version"],
                len(request.candles),
                prediction["trade_allowed"],
                elapsed_ms,
            )

            return ml_pb2.PredictSignalQualityResponse(
                prob_good_trade=prediction["prob_good_trade"],
                risk_score=prediction["risk_score"],
                trade_allowed=prediction["trade_allowed"],
                threshold=prediction["threshold"],
                risk_level=prediction["risk_level"],
                model_version=prediction["model_version"],
            )
        except ValueError as error:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
        except FileNotFoundError as error:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(error))
        except Exception as error:
            logger.exception(
                "prediction failed symbol=%s interval=%s strategy=%s",
                request.symbol,
                request.interval,
                request.strategy_name,
            )
            context.abort(
                grpc.StatusCode.INTERNAL,
                f"prediction failed: {error}",
            )

import grpc
from ml.v1 import ml_pb2
from ml.v1 import ml_pb2_grpc
from ..online.non_ml_inference import predict_signal_quality
from ..online.validation import Validator

class MLService(ml_pb2_grpc.MLServiceServicer):
    def PredictSignalQuality(self, request, context):
        validator = Validator(context, request)
        validator.validate_symbol()
        validator.validate_interval()
        validator.validate_strategy()

        features = {
            "rsi_14": request.features.rsi_14,
            "return_1": request.features.return_1,
            "return_6": request.features.return_6,
            "return_24": request.features.return_24,
            "volatility_24": request.features.volatility_24,
            "volume_zscore": request.features.volume_zscore,
            "trend_strength": request.features.trend_strength,
            "ma_distance": request.features.ma_distance,
        }

        features_validator = Validator(context, request, features)
        features_validator.validate_rsi_14()
        features_validator.validate_volatility_24()
        features_validator.validate_trend_strength()
        features_validator.validate_ma_distance()

        prediction = predict_signal_quality(features)

        prediction_validator = Validator(context, request, prediction)
        prediction_validator.validate_p_win()

        return ml_pb2.PredictSignalQualityResponse(
            p_win=prediction["p_win"],
            expected_return_pct=prediction["expected_return_pct"],
            risk_level=prediction["risk_level"],
            model_version=prediction["model_version"],
        )
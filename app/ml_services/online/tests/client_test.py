import grpc

from ml.v1 import ml_pb2
from ml.v1 import ml_pb2_grpc


channel = grpc.insecure_channel("localhost:8001")
client = ml_pb2_grpc.MLServiceStub(channel)

request = ml_pb2.PredictSignalQualityRequest(
    symbol="BTCUSDT",
    interval="1h",
    strategy="mean_reversion_rsi",
    action="buy",
    features=ml_pb2.SignalFeatures(
        rsi_14=28.5,
        return_1=-0.003,
        return_6=-0.015,
        return_24=-0.021,
        volatility_24=0.022,
        volume_zscore=1.4,
        trend_strength=0.38,
        ma_distance=-0.012,
    ),
)

response = client.PredictSignalQuality(request)

print(response)
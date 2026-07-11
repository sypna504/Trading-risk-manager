import grpc
from app.config import settings
from ml.v1 import ml_pb2
from ml.v1 import ml_pb2_grpc

class MLService:
    def __init__(self):
        addres = f"127.0.0.1:{settings.ML_SERVICE_PORT}"
        self.channel = grpc.insecure_channel(addres)
        self.client = ml_pb2_grpc.MLServiceStub(self.channel)
    
    def predict_quality(
            self,
            symbol,
            interval,
            strategy,
            action,
            features):
        
        request = ml_pb2.PredictSignalQualityRequest(
            symbol,
            interval,
            strategy,
            action,
            features
        )

        responce = self.client.PredictSignalQuality(request)
        return responce
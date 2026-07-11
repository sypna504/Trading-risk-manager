from concurrent import futures
import grpc
from ..config import settings
from ml.v1 import ml_pb2_grpc
from ..online.service import MLService

def serv():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    ml_pb2_grpc.add_MLServiceServicer_to_server(
        MLService(),
        server,
    )
    ml_port = settings.ML_SERVICE_PORT
    model_version = settings.MODEL_VERSION

    server.add_insecure_port(f"[::]:{str(ml_port)}")
    server.start()
    print(f"ML gRPC service started on port {ml_port}")
    print(f"current model {model_version}")
    server.wait_for_termination()


if __name__ == "__main__":
    serv()
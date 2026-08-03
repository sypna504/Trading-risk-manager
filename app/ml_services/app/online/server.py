from concurrent import futures

import grpc
from ml.v1 import ml_pb2_grpc

from ..config import settings
from .ml_inference import predictor
from .service import MLService


def serv():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    ml_pb2_grpc.add_MLServiceServicer_to_server(MLService(), server)
    ml_port = settings.ML_SERVICE_PORT

    server.add_insecure_port(f"[::]:{ml_port}")
    server.start()
    metadata = predictor.metadata()
    print(f"ML gRPC service started on port {ml_port}", flush=True)
    print(
        "active model: "
        f"version={metadata['model_version']}, "
        f"path={metadata['model_path']}, "
        f"threshold={metadata['threshold']}, "
        f"train_end={metadata['train_end']}, "
        f"loaded_at={metadata['loaded_at']}",
        flush=True,
    )
    server.wait_for_termination()


if __name__ == "__main__":
    serv()

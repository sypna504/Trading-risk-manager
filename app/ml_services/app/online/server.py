from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from ml.v1 import ml_pb2_grpc

from ..config import settings
from .ml_inference import predictor
from .service import MLService


def serv():
    # Importing predictor above already validates and loads the active model.
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    ml_pb2_grpc.add_MLServiceServicer_to_server(MLService(), server)
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    ml_port = settings.ML_SERVICE_PORT
    bound_port = server.add_insecure_port(f"[::]:{ml_port}")
    if bound_port == 0:
        raise RuntimeError(f"could not bind ML gRPC service to port {ml_port}")

    health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
    health_servicer.set("ml.v1.MLService", health_pb2.HealthCheckResponse.NOT_SERVING)
    server.start()
    metadata = predictor.metadata()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("ml.v1.MLService", health_pb2.HealthCheckResponse.SERVING)
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
    try:
        server.wait_for_termination()
    finally:
        health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
        health_servicer.set(
            "ml.v1.MLService", health_pb2.HealthCheckResponse.NOT_SERVING
        )


if __name__ == "__main__":
    serv()

from __future__ import annotations

import os

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc


def main() -> int:
    port = int(os.getenv("ML_SERVICE_PORT", "50051"))
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    try:
        response = health_pb2_grpc.HealthStub(channel).Check(
            health_pb2.HealthCheckRequest(service="ml.v1.MLService"),
            timeout=3,
        )
    finally:
        channel.close()
    if response.status != health_pb2.HealthCheckResponse.SERVING:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ..grpc_client import MLGrpcClient
from ..services.model_metadata_service import read_active_model_metadata


healt_router = APIRouter()
health_client = MLGrpcClient()


def _model_health() -> dict:
    try:
        metadata = read_active_model_metadata()
        config = metadata.get("config") or {}
        return {
            "model_version": metadata.get("model_version") or "unknown",
            "model_status": config.get("model_status") or "unknown",
            "model_stale": metadata.get("is_model_stale"),
            "model_files_ready": bool(
                metadata.get("model_file_exists")
                and metadata.get("config_file_exists")
            ),
        }
    except Exception:
        return {
            "model_version": "unknown",
            "model_status": "unknown",
            "model_stale": None,
            "model_files_ready": False,
        }


@healt_router.post(path="/health")
async def get_health_legacy():
    return {"status": "ok"}


@healt_router.get(path="/health")
async def get_health():
    grpc_status = health_client.health_status(timeout=2.0)
    model = _model_health()
    ready = grpc_status == "serving" and model["model_files_ready"]
    status = "ok" if ready else "degraded"
    return {
        "status": status,
        "liveness": "ok",
        "readiness": "ready" if ready else "not_ready",
        "backend": "available",
        "ml_service": grpc_status,
        **model,
        "utc_time": datetime.now(timezone.utc).isoformat(),
    }


@healt_router.get(path="/ready")
async def get_readiness():
    grpc_status = health_client.health_status(timeout=2.0)
    model = _model_health()
    ready = grpc_status == "serving" and model["model_files_ready"]
    return {
        "ready": ready,
        "ml_service": grpc_status,
        **model,
        "utc_time": datetime.now(timezone.utc).isoformat(),
    }

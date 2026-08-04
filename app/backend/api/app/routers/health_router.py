from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ..grpc_client import MLGrpcClient
from ..services.model_metadata_service import read_active_model_metadata


healt_router = APIRouter()
health_client = MLGrpcClient()


def _read_model_version() -> str:
    try:
        metadata = read_active_model_metadata()
        return str(metadata.get("model_version") or "unknown")
    except (OSError, ValueError, TypeError):
        return "unknown"


@healt_router.post(path="/health")
async def get_health_legacy():
    return {"status": "ok"}


@healt_router.get(path="/health")
async def get_health():
    ml_available = health_client.is_ready(timeout=2.0)
    return {
        "status": "ok" if ml_available else "degraded",
        "backend": "available",
        "ml_service": "available" if ml_available else "unavailable",
        "model_version": _read_model_version(),
        "utc_time": datetime.now(timezone.utc).isoformat(),
    }

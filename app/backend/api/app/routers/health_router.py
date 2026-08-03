from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from ..config import settings
from ..grpc_client import MLGrpcClient


healt_router = APIRouter()
health_client = MLGrpcClient()


def _read_model_version() -> str:
    config_path = Path(settings.MODEL_CONFIG_PATH)
    if not config_path.exists():
        return "unknown"

    try:
        return str(
            json.loads(config_path.read_text(encoding="utf-8")).get(
                "model_version",
                "unknown",
            )
        )
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

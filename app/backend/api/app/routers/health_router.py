from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from fastapi import APIRouter

from app.news_intelligence.config import LocalLLMSettings, TelegramSettings
from app.news_intelligence.storage import NewsRepository

from ..config import settings
from ..grpc_client import MLGrpcClient
from ..services.model_metadata_service import read_active_model_metadata

healt_router = APIRouter()
health_client = MLGrpcClient()

def _model_health() -> dict:
    try:
        metadata = read_active_model_metadata(); config = metadata.get("config") or {}
        return {"model_version":metadata.get("model_version") or "unknown","model_status":config.get("model_status") or "unknown","model_stale":metadata.get("is_model_stale"),"model_files_ready":bool(metadata.get("model_file_exists") and metadata.get("config_file_exists"))}
    except Exception:
        return {"model_version":"unknown","model_status":"unknown","model_stale":None,"model_files_ready":False}

def _news_health() -> str:
    try: NewsRepository(settings.DATABASE_PATH).summary(); return "ready"
    except Exception: return "degraded"

def _database_health() -> str:
    try:
        connection=sqlite3.connect(settings.DATABASE_PATH); connection.execute("SELECT 1"); connection.close(); return "ready"
    except Exception: return "degraded"

def _telegram_health() -> str:
    try:
        config=TelegramSettings.from_env(); return "ready" if config.available else "optional unavailable"
    except Exception: return "degraded"

def _llm_health() -> str:
    config=LocalLLMSettings.from_env()
    if config.provider != "ollama" or not config.model: return "optional unavailable"
    try:
        request=Request(f"{config.url.rstrip('/')}/api/tags",headers={"Accept":"application/json"})
        with urlopen(request,timeout=min(config.timeout_seconds,1.5)) as response:
            payload=json.loads(response.read().decode("utf-8"))
        return "ready" if isinstance(payload,dict) else "degraded"
    except Exception: return "degraded"

def _health_payload() -> dict:
    grpc_status=health_client.health_status(timeout=2.0); model=_model_health(); ready=grpc_status=="serving" and model["model_files_ready"]
    news_status=_news_health(); llm_status=_llm_health(); telegram_status=_telegram_health(); database_status=_database_health()
    services = {
        "backend": "ready",
        "ml_service": "ready" if grpc_status == "serving" else "degraded",
        "news_service": news_status,
        "telegram": telegram_status,
        "llm": llm_status,
        "database": database_status,
    }
    return {"status":"ok" if ready else "degraded","liveness":"ok","readiness":"ready" if ready else "not_ready","backend":"ready","ml_service":grpc_status,"news_service":news_status,"telegram":telegram_status,"llm":llm_status,"database":database_status,"services":services,**model,"utc_time":datetime.now(timezone.utc).isoformat()}

@healt_router.post(path="/health")
async def get_health_legacy(): return {"status":"ok"}
@healt_router.get(path="/health")
async def get_health(): return _health_payload()
@healt_router.get(path="/ready")
async def get_readiness():
    payload=_health_payload(); return {"ready":payload["readiness"]=="ready","ml_service":payload["ml_service"],"services":payload["services"],"model_version":payload["model_version"],"model_status":payload["model_status"],"model_stale":payload["model_stale"],"model_files_ready":payload["model_files_ready"],"utc_time":payload["utc_time"]}

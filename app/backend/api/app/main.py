from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .logging_config import configure_logging
from .middleware import RequestContextMiddleware
from .routers.agent_router import router as agent_router
from .routers.health_router import health_client, healt_router
from .routers.market_router import market_router
from .routers.ml_service_router import ml_client, ml_router
from .routers.models_router import router as models_router
from .routers.news_router import news_router
from .routers.paper_router import router as paper_router
from .routers.research_router import router as research_router
from .routers.trade_decision_router import trade_ml_client, trade_router
from app.geopolitical.router import router as geopolitical_router
from .services.outcome_service import OutcomeWorker
from .storage.database import init_database

STATIC_DIR = Path(__file__).resolve().parent / "static"
outcome_worker = OutcomeWorker()

@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    init_database()
    outcome_worker.start()
    try:
        yield
    finally:
        outcome_worker.stop()
        health_client.close()
        ml_client.close()
        trade_ml_client.close()

app = FastAPI(title="Trading Risk Manager", version="1.0.0-paper-mvp", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(healt_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(news_router, prefix="/api/v1")
app.include_router(geopolitical_router, prefix="/api/v1")
app.include_router(trade_router, prefix="/api/v1")
app.include_router(research_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(paper_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(os.getenv("FRONTEND_URL", "http://localhost:3000/"), status_code=307)

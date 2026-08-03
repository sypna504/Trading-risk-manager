from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .logging_config import configure_logging
from .middleware import RequestContextMiddleware
from .routers.health_router import health_client, healt_router
from .routers.market_router import market_router
from .routers.ml_service_router import ml_client, ml_router
from .routers.trade_decision_router import trade_ml_client, trade_router
from .storage.database import init_database


STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    init_database()
    yield
    health_client.close()
    ml_client.close()
    trade_ml_client.close()


app = FastAPI(
    title="Trading Risk Manager",
    version="0.1.0-mvp",
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(healt_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/api/v1")
app.include_router(trade_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")

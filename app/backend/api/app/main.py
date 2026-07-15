from fastapi import FastAPI
from .routers.health_router import healt_router
from .routers.market_router import market_router
from .routers.ml_service_router import ml_router

app = FastAPI()

app.include_router(healt_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/api/v1")

from __future__ import annotations

import os
from fastapi import FastAPI

from app.news_intelligence.storage import NewsRepository

app = FastAPI(title="Trading Risk Manager News Service")
repository = NewsRepository(os.getenv("DATABASE_PATH", "/app/data/trading_risk.db"))

@app.get("/health")
def health():
    try:
        repository.summary()
        return {"status":"ready","telegram":"optional","llm":os.getenv("NEWS_LLM_PROVIDER","rule_based")}
    except Exception as error:
        return {"status":"degraded","error":str(error)}

@app.get("/news")
def news(limit:int=100):
    return [item.model_dump(mode="json") for item in repository.list_news(limit=limit)]

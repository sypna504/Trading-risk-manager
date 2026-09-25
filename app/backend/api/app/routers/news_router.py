from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.news_intelligence.models import NewsItem
from app.news_intelligence.storage import NewsRepository

from ..config import settings


news_router = APIRouter(prefix="/news", tags=["news"])


def get_news_repository() -> NewsRepository:
    return NewsRepository(settings.DATABASE_PATH)


NewsRepo = Annotated[NewsRepository, Depends(get_news_repository)]


@news_router.get("", response_model=list[NewsItem])
def list_news(
    repository: NewsRepo,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    return repository.list_news(limit=limit, offset=offset)


@news_router.get("/summary")
def news_summary(repository: NewsRepo):
    return repository.summary()


@news_router.get("/symbol/{symbol}", response_model=list[NewsItem])
def news_for_symbol(
    symbol: str,
    repository: NewsRepo,
    limit: int = Query(default=50, ge=1, le=500),
):
    return repository.latest_for_symbol(symbol, limit=limit)


@news_router.get("/{news_id}", response_model=NewsItem)
def get_news(news_id: str, repository: NewsRepo):
    item = repository.get_news(news_id)
    if item is None:
        raise HTTPException(status_code=404, detail="news item not found")
    return item

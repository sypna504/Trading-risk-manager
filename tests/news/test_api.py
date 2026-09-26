from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.backend.api.app.routers.news_router import get_news_repository, news_router
from app.news_intelligence.analysis import RuleBasedNewsAnalyzer
from app.news_intelligence.normalization import NewsNormalizer
from app.news_intelligence.storage import NewsRepository


def _app(repository: NewsRepository) -> FastAPI:
    app = FastAPI()
    app.include_router(news_router, prefix="/api/v1")
    app.dependency_overrides[get_news_repository] = lambda: repository
    return app


def test_news_api_list_get_summary_and_symbol(tmp_path, make_news_item):
    repository = NewsRepository(tmp_path / "api.db")
    item = make_news_item(
        id="news-1",
        external_id="news-1",
        title="Bitcoin ETF approved with record inflow",
        text="Bitcoin adoption grows",
        published_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
    )
    item = RuleBasedNewsAnalyzer().analyze(NewsNormalizer().normalize(item))
    repository.save_news(item)

    with TestClient(_app(repository)) as client:
        listed = client.get("/api/v1/news")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == "news-1"

        fetched = client.get("/api/v1/news/news-1")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == "news-1"

        summary = client.get("/api/v1/news/summary")
        assert summary.status_code == 200
        assert summary.json()["last_24h_count"] == 1

        symbol = client.get("/api/v1/news/symbol/BTC")
        assert symbol.status_code == 200
        assert [row["id"] for row in symbol.json()] == ["news-1"]

        missing = client.get("/api/v1/news/missing")
        assert missing.status_code == 404

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.news_intelligence.models import NewsItem, NewsSourceType


FIXTURES = Path(__file__).parent / "fixtures" / "news_items.json"


@pytest.fixture(scope="session")
def news_fixture_rows() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.fixture
def make_news_item():
    def factory(**overrides) -> NewsItem:
        payload = {
            "source_id": "fixture-source",
            "source_name": "Fixture News",
            "source_type": NewsSourceType.HIGH_QUALITY_MEDIA,
            "external_id": "fixture-1",
            "title": "Bitcoin market update",
            "text": "Bitcoin remains active.",
            "url": "https://example.com/article",
            "published_at": datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc),
            "received_at": datetime(2026, 9, 25, 12, 5, tzinfo=timezone.utc),
            "language": "en",
            "credibility_score": 0.9,
        }
        payload.update(overrides)
        return NewsItem(**payload)
    return factory

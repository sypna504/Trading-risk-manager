from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.news_intelligence.models import NewsAnalysisResult, NewsSource, NewsSourceType


def test_news_item_validation_and_utc(make_news_item):
    item = make_news_item(
        published_at=datetime(2026, 9, 25, 12, 0),
        crypto_assets=["btc", "BTC", "eth"],
    )
    assert item.published_at.tzinfo is not None
    assert item.crypto_assets == ["BTC", "ETH"]


def test_news_item_rejects_invalid_score(make_news_item):
    with pytest.raises(ValidationError):
        make_news_item(crypto_relevance=1.2)


def test_source_categories_are_explicit():
    source = NewsSource(
        id="sec",
        name="SEC",
        type=NewsSourceType.OFFICIAL,
        url="https://www.sec.gov/news",
        enabled=True,
        credibility_score=0.95,
    )
    assert source.type.value == "official"


def test_structured_analysis_validation_rejects_invalid_probability():
    with pytest.raises(ValidationError):
        NewsAnalysisResult(
            sentiment="neutral",
            event_type="other",
            crypto_relevance=0.2,
            impact_direction="uncertain",
            impact_probability=1.1,
            affected_assets=[],
            uncertainty=0.8,
        )

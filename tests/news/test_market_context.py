from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.news_intelligence.context import MarketNewsContextService
from app.news_intelligence.models import (
    ImpactDirection,
    NewsEventType,
    NewsSentiment,
)
from app.news_intelligence.normalization import NewsNormalizer
from app.news_intelligence.storage import NewsRepository


def _save(repository, make_news_item, *, now, external_id, **overrides):
    payload = {
        "external_id": external_id,
        "published_at": now - timedelta(hours=1),
        "received_at": now - timedelta(minutes=59),
        "crypto_assets": ["BTC"],
        "crypto_relevance": 0.95,
        "impact_probability": 0.85,
    }
    payload.update(overrides)
    item = NewsNormalizer().normalize(make_news_item(**payload))
    return repository.save_news(item)


def test_market_context_positive_news(tmp_path, make_news_item):
    now = datetime(2026, 9, 25, 18, tzinfo=timezone.utc)
    repository = NewsRepository(tmp_path / "news.db")
    _save(
        repository,
        make_news_item,
        now=now,
        external_id="positive",
        title="Bitcoin ETF approved",
        sentiment=NewsSentiment.POSITIVE,
        event_type=NewsEventType.ETF,
        impact_direction=ImpactDirection.BULLISH,
    )

    context = MarketNewsContextService(repository).get_market_news_context("BTCUSDT", now)
    assert context["news_count"] == 1
    assert context["positive_count"] == 1
    assert context["negative_count"] == 0
    assert context["sentiment_score"] > 0


def test_market_context_negative_news(tmp_path, make_news_item):
    now = datetime(2026, 9, 25, 18, tzinfo=timezone.utc)
    repository = NewsRepository(tmp_path / "news.db")
    _save(
        repository,
        make_news_item,
        now=now,
        external_id="negative",
        title="Bitcoin exchange hack",
        sentiment=NewsSentiment.NEGATIVE,
        event_type=NewsEventType.HACK,
        impact_direction=ImpactDirection.BEARISH,
    )

    context = MarketNewsContextService(repository).get_market_news_context("BTCUSDT", now)
    assert context["news_count"] == 1
    assert context["negative_count"] == 1
    assert context["sentiment_score"] < 0
    assert context["high_impact_count"] == 1


def test_market_context_no_news(tmp_path):
    now = datetime(2026, 9, 25, 18, tzinfo=timezone.utc)
    context = MarketNewsContextService(
        NewsRepository(tmp_path / "news.db")
    ).get_market_news_context("BTCUSDT", now)
    assert context["news_count"] == 0
    assert context["sentiment_score"] == 0
    assert context["risk_level"] == "low"
    assert context["top_events"] == []


def test_stale_news_is_excluded(tmp_path, make_news_item):
    now = datetime(2026, 9, 25, 18, tzinfo=timezone.utc)
    repository = NewsRepository(tmp_path / "news.db")
    _save(
        repository,
        make_news_item,
        now=now,
        external_id="stale",
        published_at=now - timedelta(hours=25),
        received_at=now - timedelta(hours=25),
        sentiment=NewsSentiment.NEGATIVE,
        event_type=NewsEventType.REGULATION,
        impact_direction=ImpactDirection.BEARISH,
    )
    context = MarketNewsContextService(repository).get_market_news_context("BTCUSDT", now)
    assert context["news_count"] == 0


def test_future_news_is_excluded(tmp_path, make_news_item):
    now = datetime(2026, 9, 25, 18, tzinfo=timezone.utc)
    repository = NewsRepository(tmp_path / "news.db")
    _save(
        repository,
        make_news_item,
        now=now,
        external_id="future",
        published_at=now + timedelta(seconds=1),
        received_at=now,
        sentiment=NewsSentiment.NEGATIVE,
        event_type=NewsEventType.REGULATION,
        impact_direction=ImpactDirection.BEARISH,
    )
    context = MarketNewsContextService(repository).get_market_news_context("BTCUSDT", now)
    assert context["news_count"] == 0

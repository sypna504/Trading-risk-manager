from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import settings as news_settings
from .models import ImpactDirection, NewsEventType, NewsItem, NewsSentiment
from .storage import NewsRepository


_BROAD_MARKET_EVENTS = {
    NewsEventType.REGULATION,
    NewsEventType.MACRO,
    NewsEventType.GEOPOLITICAL,
    NewsEventType.EXCHANGE,
    NewsEventType.STABLECOIN,
}
_QUOTE_ASSETS = ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _base_asset(symbol: str) -> str:
    normalized = symbol.strip().upper().replace("/", "").replace("-", "")
    for quote in _QUOTE_ASSETS:
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)]
    return normalized


def _is_symbol_relevant(item: NewsItem, symbol: str) -> bool:
    base = _base_asset(symbol)
    assets = {asset.upper() for asset in item.crypto_assets}
    if base in assets or symbol.strip().upper() in assets:
        return True

    # Market-wide macro/regulatory/geopolitical news can be relevant even when
    # an article does not name one token. Very low-relevance unrelated news is
    # still excluded.
    if item.event_type in _BROAD_MARKET_EVENTS and item.crypto_relevance >= 0.20:
        return True
    if not assets and item.crypto_relevance >= news_settings.high_relevance:
        return True
    return False


def _event_risk(item: NewsItem) -> float:
    direction_factor = {
        ImpactDirection.BEARISH: 1.0,
        ImpactDirection.UNCERTAIN: 0.7,
        ImpactDirection.BULLISH: 0.25,
    }[item.impact_direction]
    relevance = max(float(item.crypto_relevance), 0.25)
    return min(1.0, float(item.impact_probability) * direction_factor * relevance)


def _category_score(items: list[NewsItem], event_type: NewsEventType) -> float:
    values = [_event_risk(item) for item in items if item.event_type == event_type]
    if not values:
        return 0.0
    # Max catches a single severe event; a small activity bonus reflects
    # repeated relevant events without allowing the score to exceed 1.
    activity_bonus = min(0.15, 0.03 * max(0, len(values) - 1))
    return round(min(1.0, max(values) + activity_bonus), 4)


def _risk_level(
    items: list[NewsItem],
    *,
    geopolitical: float,
    regulatory: float,
    macro: float,
) -> str:
    positive = sum(item.sentiment == NewsSentiment.POSITIVE for item in items)
    negative = sum(item.sentiment == NewsSentiment.NEGATIVE for item in items)
    bearish_high_impact = sum(
        item.impact_direction == ImpactDirection.BEARISH
        and item.impact_probability >= news_settings.high_impact_probability
        and item.crypto_relevance >= news_settings.high_relevance
        for item in items
    )
    category_risk = max(geopolitical, regulatory, macro)
    if category_risk >= 0.75 or bearish_high_impact >= 2 or negative >= positive + 3:
        return "high"
    if category_risk >= 0.45 or bearish_high_impact >= 1 or negative > positive:
        return "medium"
    return "low"


class MarketNewsContextService:
    """Build decision-time-safe informational news context for one symbol."""

    def __init__(self, repository: NewsRepository) -> None:
        self.repository = repository

    def get_market_news_context(
        self,
        symbol: str,
        now: datetime,
    ) -> dict[str, object]:
        current = _utc(now)
        window_hours = news_settings.market_context_window_hours
        cutoff = current - timedelta(hours=window_hours)

        candidates = self.repository.list_published_between(
            start=cutoff,
            end=current,
            limit=2000,
        )
        items = [item for item in candidates if _is_symbol_relevant(item, symbol)]

        positive_count = sum(item.sentiment == NewsSentiment.POSITIVE for item in items)
        negative_count = sum(item.sentiment == NewsSentiment.NEGATIVE for item in items)
        news_count = len(items)
        sentiment_score = (
            (positive_count - negative_count) / news_count if news_count else 0.0
        )
        high_impact_count = sum(
            item.impact_probability >= news_settings.high_impact_probability
            and item.crypto_relevance >= news_settings.high_relevance
            for item in items
        )

        geopolitical = _category_score(items, NewsEventType.GEOPOLITICAL)
        regulatory = _category_score(items, NewsEventType.REGULATION)
        macro = _category_score(items, NewsEventType.MACRO)
        risk_level = _risk_level(
            items,
            geopolitical=geopolitical,
            regulatory=regulatory,
            macro=macro,
        )

        ranked = sorted(
            items,
            key=lambda item: (
                float(item.impact_probability) * max(float(item.crypto_relevance), 0.1),
                item.published_at,
            ),
            reverse=True,
        )[: news_settings.market_context_top_events]

        top_events = [
            {
                "id": item.id,
                "title": item.title,
                "source": item.source_name,
                "published_at": item.published_at.isoformat(),
                "event_type": item.event_type.value,
                "sentiment": item.sentiment.value,
                "impact_direction": item.impact_direction.value,
                "impact_probability": float(item.impact_probability),
                "crypto_relevance": float(item.crypto_relevance),
                "affected_assets": list(item.crypto_assets),
                "url": item.url,
            }
            for item in ranked
        ]

        return {
            "symbol": symbol.strip().upper(),
            "window_hours": window_hours,
            "news_count": news_count,
            "sentiment_score": round(sentiment_score, 4),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "high_impact_count": high_impact_count,
            "geopolitical_risk_score": geopolitical,
            "regulatory_risk_score": regulatory,
            "macro_risk_score": macro,
            "risk_level": risk_level,
            "top_events": top_events,
        }

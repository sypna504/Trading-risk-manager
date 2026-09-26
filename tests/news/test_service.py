from __future__ import annotations

from datetime import datetime, timezone

from app.news_intelligence.ingestion import RSSNewsSource
from app.news_intelligence.models import NewsSource, NewsSourceType
from app.news_intelligence.service import NewsIntelligenceService
from app.news_intelligence.storage import NewsRepository


RSS = """<rss><channel>
<item><guid>1</guid><title>Bitcoin ETF approved</title><description>Strong inflows</description><link>https://example.com/a</link></item>
<item><guid>2</guid><title> Bitcoin  ETF approved </title><description>Strong inflows</description><link>https://example.com/a?utm_source=x</link></item>
</channel></rss>"""


def test_service_ingest_is_offline_and_deduplicates(tmp_path):
    source = NewsSource(
        id="rss",
        name="RSS",
        type=NewsSourceType.SPECIALIZED_CRYPTO,
        url="https://example.com/rss",
        credibility_score=0.8,
    )
    adapter = RSSNewsSource(
        source,
        fetcher=lambda _url: RSS,
        clock=lambda: datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
    )
    repository = NewsRepository(tmp_path / "news.db")
    service = NewsIntelligenceService(repository)
    result = service.ingest(adapter)
    assert len(result) == 2
    assert result[0].id == result[1].id
    assert len(repository.list_news()) == 1

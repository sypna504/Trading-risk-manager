from __future__ import annotations

from datetime import datetime, timezone

from app.news_intelligence.ingestion import RSSNewsSource
from app.news_intelligence.models import NewsSource, NewsSourceType


RSS = """<?xml version="1.0"?>
<rss><channel><title>Fixture</title>
<item><guid>abc-1</guid><title>Bitcoin ETF approved</title>
<description>Strong inflows</description><link>https://example.com/a</link>
<pubDate>Thu, 25 Sep 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""


def test_rss_adapter_uses_injected_fetcher_without_network():
    source = NewsSource(
        id="fixture-rss",
        name="Fixture RSS",
        type=NewsSourceType.HIGH_QUALITY_MEDIA,
        url="https://example.com/rss.xml",
        credibility_score=0.9,
    )
    adapter = RSSNewsSource(
        source,
        fetcher=lambda _url: RSS,
        clock=lambda: datetime(2026, 9, 25, 10, 5, tzinfo=timezone.utc),
    )
    items = adapter.fetch()
    assert len(items) == 1
    assert items[0].external_id == "abc-1"
    assert items[0].published_at.tzinfo is not None

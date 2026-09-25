from __future__ import annotations

from app.news_intelligence.deduplication import NewsDeduplicator
from app.news_intelligence.normalization import NewsNormalizer


def test_duplicate_detection_by_normalized_hash(make_news_item):
    normalizer = NewsNormalizer()
    canonical = normalizer.normalize(
        make_news_item(id="canonical", title="Bitcoin ETF approved", text="Strong inflows", url="https://example.com/a?utm_source=x")
    )
    duplicate = normalizer.normalize(
        make_news_item(id="copy", title=" Bitcoin  ETF approved ", text="Strong inflows", url="https://example.com/a?utm_medium=y")
    )
    found = NewsDeduplicator.find_duplicate(duplicate, [canonical])
    assert found is canonical
    marked = NewsDeduplicator.mark_duplicate(duplicate, canonical)
    assert marked.is_duplicate is True
    assert marked.duplicate_group_id == "canonical"

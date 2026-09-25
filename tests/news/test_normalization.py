from __future__ import annotations

from app.news_intelligence.normalization import NewsNormalizer


def test_normalization_trims_whitespace_url_and_generates_hashes(make_news_item):
    item = make_news_item(
        title="  Bitcoin    ETF \n approved  ",
        text=" <p>Strong   inflows</p>\n today ",
        url="HTTPS://Example.COM/news/?utm_source=x&b=2&a=1#fragment",
    )
    result = NewsNormalizer().normalize(item)
    assert result.title == "Bitcoin ETF approved"
    assert result.text == "Strong inflows today"
    assert result.url == "https://example.com/news?a=1&b=2"
    assert len(result.raw_hash) == 64
    assert len(result.normalized_hash) == 64


def test_normalized_hash_is_stable_for_whitespace_and_tracking_changes(make_news_item):
    normalizer = NewsNormalizer()
    first = normalizer.normalize(
        make_news_item(title="Bitcoin ETF approved", text="Strong inflows", url="https://example.com/a?utm_source=x")
    )
    second = normalizer.normalize(
        make_news_item(title=" Bitcoin   ETF approved ", text="Strong   inflows", url="https://EXAMPLE.com/a?utm_medium=y")
    )
    assert first.raw_hash != second.raw_hash
    assert first.normalized_hash == second.normalized_hash

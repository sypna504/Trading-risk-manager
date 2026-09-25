from __future__ import annotations

from app.news_intelligence.analysis import RuleBasedNewsAnalyzer
from app.news_intelligence.normalization import NewsNormalizer


def test_rule_analyzer_fixture_cases(news_fixture_rows, make_news_item):
    analyzer = RuleBasedNewsAnalyzer()
    normalizer = NewsNormalizer()
    for index, fixture in enumerate(news_fixture_rows):
        item = make_news_item(
            external_id=f"fixture-{index}",
            title=fixture["title"],
            text=fixture["text"],
            url=fixture["url"],
        )
        result = analyzer.analyze(normalizer.normalize(item))
        assert result.event_type.value == fixture["expected_event"], fixture["name"]
        assert result.sentiment.value == fixture["expected_sentiment"], fixture["name"]
        assert result.impact_direction.value == fixture["expected_direction"], fixture["name"]
        if fixture.get("expected_asset"):
            assert fixture["expected_asset"] in result.crypto_assets
        assert 0 <= result.crypto_relevance <= 1
        assert 0 <= result.impact_probability <= 1
        assert 0 <= result.uncertainty <= 1


def test_unrelated_news_has_low_crypto_relevance(news_fixture_rows, make_news_item):
    fixture = next(row for row in news_fixture_rows if row["name"] == "unrelated")
    result = RuleBasedNewsAnalyzer().analyze(
        NewsNormalizer().normalize(make_news_item(title=fixture["title"], text=fixture["text"], url=fixture["url"]))
    )
    assert result.crypto_relevance <= 0.1

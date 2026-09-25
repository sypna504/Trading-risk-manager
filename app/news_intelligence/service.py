from __future__ import annotations

import logging

from .analysis import NewsAnalyzer, RuleBasedNewsAnalyzer, build_news_analyzer_from_env
from .context import MarketNewsContextService
from .deduplication import NewsDeduplicator
from .ingestion.base import BaseNewsSource
from .models import NewsItem
from .normalization import NewsNormalizer
from .storage import NewsRepository


logger = logging.getLogger(__name__)


class NewsIntelligenceService:
    """News pipeline isolated from Quant Core trade decisions."""

    def __init__(
        self,
        repository: NewsRepository,
        *,
        normalizer: NewsNormalizer | None = None,
        analyzer: NewsAnalyzer | None = None,
        deduplicator: NewsDeduplicator | None = None,
    ) -> None:
        self.repository = repository
        self.normalizer = normalizer or NewsNormalizer()
        self.analyzer = analyzer or build_news_analyzer_from_env()
        self.deduplicator = deduplicator or NewsDeduplicator()
        self._hard_fallback = RuleBasedNewsAnalyzer()

    def process(self, item: NewsItem) -> NewsItem:
        normalized = self.normalizer.normalize(item)
        try:
            analyzed = self.analyzer.analyze(normalized)
        except Exception as error:
            logger.warning("news analyzer failed, using rule fallback: %s", error)
            analyzed = self._hard_fallback.analyze(normalized)

        canonical = self.repository.find_duplicate(analyzed)
        if canonical is not None:
            same_external = (
                analyzed.external_id
                and canonical.source_id == analyzed.source_id
                and canonical.external_id == analyzed.external_id
            )
            if not same_external:
                return canonical
        return self.repository.save_news(analyzed)

    def ingest(self, source: BaseNewsSource) -> list[NewsItem]:
        return [self.process(item) for item in source.fetch()]

    def get_market_news_context(self, symbol: str, now) -> dict[str, object]:
        return MarketNewsContextService(self.repository).get_market_news_context(symbol, now)

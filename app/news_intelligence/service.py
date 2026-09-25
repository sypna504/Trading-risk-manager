from __future__ import annotations

from .analysis import RuleBasedNewsAnalyzer
from .deduplication import NewsDeduplicator
from .ingestion.base import BaseNewsSource
from .models import NewsItem
from .normalization import NewsNormalizer
from .storage import NewsRepository


class NewsIntelligenceService:
    """Ingestion pipeline isolated from Quant Core decisions."""

    def __init__(
        self,
        repository: NewsRepository,
        *,
        normalizer: NewsNormalizer | None = None,
        analyzer: RuleBasedNewsAnalyzer | None = None,
        deduplicator: NewsDeduplicator | None = None,
    ) -> None:
        self.repository = repository
        self.normalizer = normalizer or NewsNormalizer()
        self.analyzer = analyzer or RuleBasedNewsAnalyzer()
        self.deduplicator = deduplicator or NewsDeduplicator()

    def process(self, item: NewsItem) -> NewsItem:
        normalized = self.normalizer.normalize(item)
        analyzed = self.analyzer.analyze(normalized)
        canonical = self.repository.find_duplicate(analyzed)
        if canonical is not None:
            return canonical
        return self.repository.save_news(analyzed)

    def ingest(self, source: BaseNewsSource) -> list[NewsItem]:
        return [self.process(item) for item in source.fetch()]

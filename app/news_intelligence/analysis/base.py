from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import NewsItem


class NewsAnalyzer(ABC):
    @abstractmethod
    def analyze(self, item: NewsItem) -> NewsItem:
        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import NewsItem, NewsSource


class BaseNewsSource(ABC):
    def __init__(self, source: NewsSource) -> None:
        self.source = source

    @abstractmethod
    def fetch(self) -> list[NewsItem]:
        """Fetch source items without persisting or scoring them."""
        raise NotImplementedError

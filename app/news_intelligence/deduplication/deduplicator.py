from __future__ import annotations

from collections.abc import Iterable

from ..models import NewsItem


class NewsDeduplicator:
    """Exact-hash deduplication for MVP-1; embeddings intentionally excluded."""

    @staticmethod
    def find_duplicate(item: NewsItem, candidates: Iterable[NewsItem]) -> NewsItem | None:
        for candidate in candidates:
            if item.raw_hash and item.raw_hash == candidate.raw_hash:
                return candidate
            if item.normalized_hash and item.normalized_hash == candidate.normalized_hash:
                return candidate
        return None

    @staticmethod
    def mark_duplicate(item: NewsItem, canonical: NewsItem) -> NewsItem:
        return item.model_copy(
            update={
                "duplicate_group_id": canonical.duplicate_group_id or canonical.id,
                "is_duplicate": True,
            }
        )

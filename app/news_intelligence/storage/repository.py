from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import settings as news_settings
from ..models import NewsItem


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS news_items (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    external_id TEXT,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT,
    published_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    edited_at TEXT,
    language TEXT NOT NULL,
    crypto_assets TEXT NOT NULL,
    event_type TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    crypto_relevance REAL NOT NULL,
    impact_direction TEXT NOT NULL,
    impact_probability REAL NOT NULL,
    uncertainty REAL NOT NULL DEFAULT 1.0,
    credibility_score REAL NOT NULL,
    raw_hash TEXT NOT NULL,
    normalized_hash TEXT NOT NULL,
    duplicate_group_id TEXT,
    is_duplicate INTEGER NOT NULL DEFAULT 0,
    channel TEXT,
    message_id INTEGER
)
"""


class NewsRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, name: str, definition: str) -> None:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(news_items)")}
        if name not in columns:
            connection.execute(f"ALTER TABLE news_items ADD COLUMN {name} {definition}")

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(_CREATE_SQL)
            self._ensure_column(connection, "edited_at", "TEXT")
            self._ensure_column(connection, "uncertainty", "REAL NOT NULL DEFAULT 1.0")
            self._ensure_column(connection, "channel", "TEXT")
            self._ensure_column(connection, "message_id", "INTEGER")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_items(published_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_items(sentiment)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_raw_hash ON news_items(raw_hash)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_normalized_hash ON news_items(normalized_hash)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_source_external ON news_items(source_id, external_id)"
            )
            connection.commit()

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> NewsItem:
        payload = dict(row)
        payload["crypto_assets"] = json.loads(payload["crypto_assets"] or "[]")
        payload["is_duplicate"] = bool(payload["is_duplicate"])
        return NewsItem.model_validate(payload)

    def find_duplicate(self, item: NewsItem) -> NewsItem | None:
        if not item.raw_hash and not item.normalized_hash:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM news_items
                WHERE (raw_hash <> '' AND raw_hash = ?)
                   OR (normalized_hash <> '' AND normalized_hash = ?)
                ORDER BY published_at ASC
                LIMIT 1
                """,
                (item.raw_hash, item.normalized_hash),
            ).fetchone()
        return self._row_to_item(row) if row else None

    def find_by_external_id(self, source_id: str, external_id: str | None) -> NewsItem | None:
        if not external_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM news_items WHERE source_id = ? AND external_id = ? LIMIT 1",
                (source_id, external_id),
            ).fetchone()
        return self._row_to_item(row) if row else None

    @staticmethod
    def _values(item: NewsItem) -> tuple:
        payload = item.model_dump(mode="json")
        return (
            payload["source_id"], payload["source_name"], payload["source_type"],
            payload["external_id"], payload["title"], payload["text"], payload["url"],
            payload["published_at"], payload["received_at"], payload["edited_at"],
            payload["language"], json.dumps(payload["crypto_assets"], ensure_ascii=False),
            payload["event_type"], payload["sentiment"], payload["crypto_relevance"],
            payload["impact_direction"], payload["impact_probability"], payload["uncertainty"],
            payload["credibility_score"], payload["raw_hash"], payload["normalized_hash"],
            payload["duplicate_group_id"], int(payload["is_duplicate"]), payload["channel"],
            payload["message_id"],
        )

    def save_news(self, item: NewsItem) -> NewsItem:
        """Insert canonical news; source/external_id acts as an edit-aware identity."""
        with self._connect() as connection:
            existing_external = None
            if item.external_id:
                existing_external = connection.execute(
                    "SELECT * FROM news_items WHERE source_id = ? AND external_id = ? LIMIT 1",
                    (item.source_id, item.external_id),
                ).fetchone()
            if existing_external is not None:
                stable_id = str(existing_external["id"])
                updated = item.model_copy(update={"id": stable_id})
                connection.execute(
                    """
                    UPDATE news_items SET
                        source_id=?, source_name=?, source_type=?, external_id=?, title=?, text=?, url=?,
                        published_at=?, received_at=?, edited_at=?, language=?, crypto_assets=?, event_type=?,
                        sentiment=?, crypto_relevance=?, impact_direction=?, impact_probability=?, uncertainty=?,
                        credibility_score=?, raw_hash=?, normalized_hash=?, duplicate_group_id=?, is_duplicate=?,
                        channel=?, message_id=?
                    WHERE id=?
                    """,
                    self._values(updated) + (stable_id,),
                )
                connection.commit()
                return updated

            existing = connection.execute(
                """
                SELECT * FROM news_items
                WHERE (raw_hash <> '' AND raw_hash = ?)
                   OR (normalized_hash <> '' AND normalized_hash = ?)
                ORDER BY published_at ASC
                LIMIT 1
                """,
                (item.raw_hash, item.normalized_hash),
            ).fetchone()
            if existing is not None:
                return self._row_to_item(existing)

            payload = item.model_dump(mode="json")
            connection.execute(
                """
                INSERT INTO news_items (
                    id, source_id, source_name, source_type, external_id,
                    title, text, url, published_at, received_at, edited_at, language,
                    crypto_assets, event_type, sentiment, crypto_relevance,
                    impact_direction, impact_probability, uncertainty, credibility_score,
                    raw_hash, normalized_hash, duplicate_group_id, is_duplicate, channel, message_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (payload["id"],) + self._values(item),
            )
            connection.commit()
        return item

    def list_news(self, *, limit: int = 100, offset: int = 0) -> list[NewsItem]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM news_items ORDER BY published_at DESC, received_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def get_news(self, news_id: str) -> NewsItem | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM news_items WHERE id = ?", (news_id,)
            ).fetchone()
        return self._row_to_item(row) if row else None

    def latest_for_symbol(self, symbol: str, *, limit: int = 50) -> list[NewsItem]:
        target = symbol.strip().upper()
        if not target:
            return []
        candidates = self.list_news(limit=min(max(limit * 10, 100), 500))
        return [item for item in candidates if target in item.crypto_assets][:limit]

    def summary(self, *, now: datetime | None = None) -> dict[str, int | str]:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        cutoff = current.astimezone(timezone.utc) - timedelta(hours=24)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sentiment, impact_probability, crypto_relevance, impact_direction "
                "FROM news_items WHERE published_at >= ?",
                (cutoff.isoformat(),),
            ).fetchall()
        counts = {"positive": 0, "negative": 0, "neutral": 0}
        high_impact = 0
        high_impact_bearish = 0
        for row in rows:
            sentiment = str(row["sentiment"])
            if sentiment in counts:
                counts[sentiment] += 1
            high = (
                float(row["impact_probability"]) >= news_settings.high_impact_probability
                and float(row["crypto_relevance"]) >= news_settings.high_relevance
            )
            if high:
                high_impact += 1
                if str(row["impact_direction"]) == "bearish":
                    high_impact_bearish += 1
        if high_impact_bearish >= 2 or counts["negative"] >= counts["positive"] + 3:
            risk_level = "high"
        elif high_impact_bearish >= 1 or counts["negative"] > counts["positive"]:
            risk_level = "medium"
        else:
            risk_level = "low"
        return {
            "last_24h_count": len(rows),
            **counts,
            "high_impact": high_impact,
            "risk_level": risk_level,
        }

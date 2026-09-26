from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import GeopoliticalEvent


class GeopoliticalEventRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS geopolitical_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    known_at TEXT NOT NULL,
                    event_time TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_geo_known_at ON geopolitical_events(known_at)"
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, event: GeopoliticalEvent) -> GeopoliticalEvent:
        payload = event.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO geopolitical_events(
                    event_id, event_type, payload_json, published_at, received_at, known_at, event_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    event_type=excluded.event_type,
                    payload_json=excluded.payload_json,
                    published_at=excluded.published_at,
                    received_at=excluded.received_at,
                    known_at=excluded.known_at,
                    event_time=excluded.event_time
                """,
                (
                    event.event_id, event.event_type.value, json.dumps(payload, ensure_ascii=False),
                    event.published_at.isoformat(), event.received_at.isoformat(),
                    event.known_at.isoformat(), event.event_time.isoformat() if event.event_time else None,
                ),
            )
            connection.commit()
        return event

    def get(self, event_id: str) -> GeopoliticalEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM geopolitical_events WHERE event_id=?", (event_id,)
            ).fetchone()
        return GeopoliticalEvent.model_validate(json.loads(row["payload_json"])) if row else None

    def list_recent(self, limit: int = 100) -> list[GeopoliticalEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM geopolitical_events ORDER BY known_at DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [GeopoliticalEvent.model_validate(json.loads(row["payload_json"])) for row in rows]

    def list_known_at(self, timestamp: datetime, limit: int = 1000) -> list[GeopoliticalEvent]:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM geopolitical_events
                   WHERE julianday(known_at) <= julianday(?)
                   ORDER BY julianday(known_at) DESC LIMIT ?""",
                (timestamp.isoformat(), max(1, min(limit, 5000))),
            ).fetchall()
        return [GeopoliticalEvent.model_validate(json.loads(row["payload_json"])) for row in rows]

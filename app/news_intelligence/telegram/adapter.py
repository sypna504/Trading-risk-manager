from __future__ import annotations

import asyncio
import inspect
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from ..config import TelegramSettings
from ..models import NewsItem, NewsSourceType
from ..source_config import load_news_sources_config


logger = logging.getLogger(__name__)
ClientFactory = Callable[[str, int, str], Any]


def _default_client_factory(session_path: str, api_id: int, api_hash: str):
    try:
        from telethon import TelegramClient
    except ImportError as error:  # Telegram remains optional for non-Telegram runs
        raise RuntimeError("Telethon is not installed") from error
    return TelegramClient(session_path, api_id, api_hash)


async def _maybe_await(value):
    return await value if inspect.isawaitable(value) else value


def _safe_channel_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lstrip("@")).strip("-")
    return cleaned[:100] or "unknown"


def _channel_username(message: Any, configured_channel: str) -> str | None:
    chat = getattr(message, "chat", None)
    username = getattr(chat, "username", None)
    if username:
        return str(username).lstrip("@")
    candidate = configured_channel.strip()
    if candidate.startswith("@"):
        return candidate[1:]
    if candidate.startswith("https://t.me/"):
        tail = candidate.removeprefix("https://t.me/").strip("/")
        if tail and "/" not in tail:
            return tail
    if candidate and all(ch.isalnum() or ch in "_" for ch in candidate):
        return candidate
    return None


def _channel_display_name(message: Any, configured_channel: str) -> str:
    chat = getattr(message, "chat", None)
    for attr in ("title", "username"):
        value = getattr(chat, attr, None)
        if value:
            return str(value)
    return configured_channel.strip() or "telegram"


class TelegramNewsSource:
    """Optional Telethon adapter. Real Telegram is never required by CI."""

    def __init__(
        self,
        channels: list[str],
        *,
        enabled: bool = True,
        api_id: int | None = None,
        api_hash: str | None = None,
        session_path: str | None = None,
        limit_per_channel: int = 50,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.0,
        client_factory: ClientFactory | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        env = TelegramSettings.from_env()
        self.channels = [channel.strip() for channel in channels if channel.strip()]
        self.enabled = enabled
        self.api_id = api_id if api_id is not None else env.api_id
        self.api_hash = api_hash if api_hash is not None else env.api_hash
        self.session_path = session_path if session_path is not None else env.session_path
        self.limit_per_channel = max(1, int(limit_per_channel))
        self.max_retries = max(0, int(max_retries))
        self.retry_delay_seconds = max(0.0, float(retry_delay_seconds))
        self.client_factory = client_factory or _default_client_factory
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @classmethod
    def from_config(
        cls,
        path: str = "config/news_sources.yaml",
        **kwargs,
    ) -> "TelegramNewsSource":
        config = load_news_sources_config(path).telegram
        return cls(
            config.channels,
            enabled=config.enabled,
            **kwargs,
        )

    @property
    def available(self) -> bool:
        return bool(
            self.enabled
            and self.channels
            and self.api_id
            and self.api_hash
            and self.session_path
        )

    @staticmethod
    def parse_message(
        message: Any,
        configured_channel: str,
        *,
        received_at: datetime,
    ) -> NewsItem | None:
        raw_text = getattr(message, "message", None)
        if raw_text is None:
            raw_text = getattr(message, "text", None)
        text = str(raw_text or "").strip()
        if not text:
            return None

        raw_message_id = getattr(message, "id", None)
        try:
            message_id = int(raw_message_id)
        except (TypeError, ValueError):
            return None
        if message_id <= 0:
            return None

        published_at = getattr(message, "date", None) or received_at
        edited_at = getattr(message, "edit_date", None)
        channel = _channel_display_name(message, configured_channel)
        username = _channel_username(message, configured_channel)
        url = f"https://t.me/{username}/{message_id}" if username else None
        title = next((line.strip() for line in text.splitlines() if line.strip()), text)
        title = title[:2048]
        source_key = _safe_channel_id(username or channel)

        return NewsItem(
            source_id=f"telegram:{source_key.lower()}",
            source_name=channel[:256],
            source_type=NewsSourceType.SOCIAL,
            external_id=f"telegram:{source_key.lower()}:{message_id}",
            title=title,
            text=text,
            url=url,
            published_at=published_at,
            received_at=received_at,
            edited_at=edited_at,
            language="unknown",
            credibility_score=0.5,
            channel=channel[:256],
            message_id=message_id,
        )

    async def fetch_async(self) -> list[NewsItem]:
        if not self.available:
            return []

        for attempt in range(self.max_retries + 1):
            client = None
            try:
                client = self.client_factory(
                    str(self.session_path), int(self.api_id), str(self.api_hash)
                )
                await _maybe_await(client.connect())
                is_connected = getattr(client, "is_connected", None)
                if callable(is_connected) and not bool(is_connected()):
                    raise ConnectionError("Telegram client is disconnected")

                is_authorized = getattr(client, "is_user_authorized", None)
                if callable(is_authorized):
                    authorized = await _maybe_await(is_authorized())
                    if not authorized:
                        logger.warning("Telegram session is not authorized")
                        return []

                received_at = self.clock()
                if received_at.tzinfo is None:
                    received_at = received_at.replace(tzinfo=timezone.utc)
                received_at = received_at.astimezone(timezone.utc)

                result: list[NewsItem] = []
                for channel in self.channels:
                    async for message in client.iter_messages(
                        channel, limit=self.limit_per_channel
                    ):
                        item = self.parse_message(
                            message,
                            channel,
                            received_at=received_at,
                        )
                        if item is not None:
                            result.append(item)
                return result
            except Exception as error:
                if attempt >= self.max_retries:
                    logger.warning("Telegram ingestion disabled for this run: %s", error)
                    return []
                if self.retry_delay_seconds:
                    await asyncio.sleep(self.retry_delay_seconds)
            finally:
                if client is not None:
                    disconnect = getattr(client, "disconnect", None)
                    if callable(disconnect):
                        try:
                            await _maybe_await(disconnect())
                        except Exception:
                            pass
        return []

    def fetch(self) -> list[NewsItem]:
        if not self.available:
            return []
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.fetch_async())
        logger.warning("TelegramNewsSource.fetch() called inside a running event loop; use fetch_async()")
        return []

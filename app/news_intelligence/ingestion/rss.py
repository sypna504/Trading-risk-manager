from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ..models import NewsItem, NewsSource
from .base import BaseNewsSource


Fetcher = Callable[[str], str | bytes]


def _default_fetcher(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "TradingRiskManager-News/1.0"})
    with urlopen(request, timeout=15) as response:  # noqa: S310 - configured RSS URL
        return response.read()


def _text(element, *names: str) -> str:
    for name in names:
        child = element.find(name)
        if child is not None and child.text:
            return child.text
    return ""


def _parse_timestamp(value: str, fallback: datetime) -> datetime:
    raw = value.strip()
    if not raw:
        return fallback
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class RSSNewsSource(BaseNewsSource):
    """Minimal RSS/Atom adapter with injectable transport for offline CI."""

    def __init__(
        self,
        source: NewsSource,
        *,
        fetcher: Fetcher | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(source)
        self.fetcher = fetcher or _default_fetcher
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def fetch(self) -> list[NewsItem]:
        if not self.source.enabled:
            return []
        payload = self.fetcher(self.source.url)
        root = ElementTree.fromstring(payload)
        received_at = self.clock().astimezone(timezone.utc)

        items = root.findall(".//item")
        if not items:
            ns = "{http://www.w3.org/2005/Atom}"
            items = root.findall(f".//{ns}entry")

        result: list[NewsItem] = []
        for index, item in enumerate(items):
            atom = item.tag.endswith("entry")
            prefix = "{http://www.w3.org/2005/Atom}" if atom else ""
            title = _text(item, f"{prefix}title").strip()
            if not title:
                continue
            text = _text(
                item,
                f"{prefix}description",
                f"{prefix}summary",
                f"{prefix}content",
            )
            link = ""
            link_element = item.find(f"{prefix}link")
            if link_element is not None:
                link = (link_element.get("href") or link_element.text or "").strip()
            external_id = _text(item, f"{prefix}guid", f"{prefix}id").strip() or link or f"rss-{index}"
            published_raw = _text(
                item,
                f"{prefix}pubDate",
                f"{prefix}published",
                f"{prefix}updated",
            )
            result.append(
                NewsItem(
                    source_id=self.source.id,
                    source_name=self.source.name,
                    source_type=self.source.type,
                    external_id=external_id,
                    title=title,
                    text=text,
                    url=link or None,
                    published_at=_parse_timestamp(published_raw, received_at),
                    received_at=received_at,
                    language="unknown",
                    credibility_score=self.source.credibility_score,
                )
            )
        return result

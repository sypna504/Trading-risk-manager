from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ..models import NewsItem


_WHITESPACE = re.compile(r"\s+")
_HTML_TAG = re.compile(r"<[^>]+>")
_TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = _HTML_TAG.sub(" ", value)
    return _WHITESPACE.sub(" ", value).strip()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalized_url(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    filtered = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(sorted(filtered)),
            "",
        )
    )


def _sha256(*parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class NewsNormalizer:
    def normalize(self, item: NewsItem) -> NewsItem:
        raw_title = item.title
        raw_text = item.text
        raw_url = item.url or ""
        title = _clean_text(item.title)
        text = _clean_text(item.text)
        url = _normalized_url(item.url)

        raw_hash = _sha256(raw_title, raw_text, raw_url)
        normalized_hash = _sha256(
            title.casefold(),
            text.casefold(),
            (url or "").casefold(),
        )
        return item.model_copy(
            update={
                "title": title,
                "text": text,
                "url": url,
                "published_at": _utc(item.published_at),
                "received_at": _utc(item.received_at),
                "edited_at": _utc(item.edited_at) if item.edited_at else None,
                "raw_hash": raw_hash,
                "normalized_hash": normalized_hash,
            }
        )

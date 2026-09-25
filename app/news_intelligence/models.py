from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


Score = Annotated[float, Field(ge=0.0, le=1.0)]


class NewsSourceType(str, Enum):
    OFFICIAL = "official"
    HIGH_QUALITY_MEDIA = "high_quality_media"
    SPECIALIZED_CRYPTO = "specialized_crypto"
    SOCIAL = "social"
    UNVERIFIED = "unverified"


class NewsSentiment(str, Enum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class NewsEventType(str, Enum):
    REGULATION = "regulation"
    ETF = "etf"
    EXCHANGE = "exchange"
    HACK = "hack"
    STABLECOIN = "stablecoin"
    MACRO = "macro"
    GEOPOLITICAL = "geopolitical"
    TOKEN_SPECIFIC = "token_specific"
    OTHER = "other"


class ImpactDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    UNCERTAIN = "uncertain"


class NewsSource(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    type: NewsSourceType
    url: str = Field(min_length=1, max_length=2048)
    enabled: bool = True
    credibility_score: Score = 0.5


class NewsItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128)
    source_name: str = Field(min_length=1, max_length=256)
    source_type: NewsSourceType
    external_id: str | None = Field(default=None, max_length=512)

    title: str = Field(min_length=1, max_length=2048)
    text: str = Field(default="", max_length=100_000)
    url: str | None = Field(default=None, max_length=4096)

    published_at: datetime
    received_at: datetime

    language: str = Field(default="unknown", min_length=2, max_length=32)
    crypto_assets: list[str] = Field(default_factory=list)

    event_type: NewsEventType = NewsEventType.OTHER
    sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    crypto_relevance: Score = 0.0
    impact_direction: ImpactDirection = ImpactDirection.UNCERTAIN
    impact_probability: Score = 0.0

    credibility_score: Score = 0.5

    raw_hash: str = Field(default="", max_length=128)
    normalized_hash: str = Field(default="", max_length=128)

    duplicate_group_id: str | None = Field(default=None, max_length=128)
    is_duplicate: bool = False

    @field_validator("published_at", "received_at")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("crypto_assets")
    @classmethod
    def normalize_assets(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            asset = str(value).strip().upper()
            if asset and asset not in normalized:
                normalized.append(asset)
        return normalized

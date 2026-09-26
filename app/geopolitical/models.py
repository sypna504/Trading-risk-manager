from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

Score = Annotated[float, Field(ge=0.0, le=1.0)]


class GeopoliticalEventType(str, Enum):
    ARMED_CONFLICT_ESCALATION = "armed_conflict_escalation"
    ARMED_CONFLICT_DEESCALATION = "armed_conflict_deescalation"
    SANCTIONS = "sanctions"
    TARIFFS = "tariffs"
    TRADE_RESTRICTIONS = "trade_restrictions"
    CAPITAL_CONTROLS = "capital_controls"
    BANKING_CRISIS = "banking_crisis"
    SOVEREIGN_RISK = "sovereign_risk"
    DIPLOMATIC_MEETING = "diplomatic_meeting"
    CENTRAL_BANK_STATEMENT = "central_bank_statement"
    GOVERNMENT_STATEMENT = "government_statement"
    REGULATION = "regulation"
    MACRO_RELEASE = "macro_release"
    EMERGENCY_EVENT = "emergency_event"
    OTHER = "other"


class RiskDirection(str, Enum):
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class GeopoliticalEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    event_type: GeopoliticalEventType
    published_at: datetime
    received_at: datetime
    known_at: datetime
    event_time: datetime | None = None

    countries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    persons: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)

    severity: Score = 0.0
    uncertainty: Score = 1.0
    crypto_relevance: Score = 0.0
    risk_on_off_direction: RiskDirection = RiskDirection.UNCERTAIN
    affected_assets: list[str] = Field(default_factory=list)

    source_ids: list[str] = Field(default_factory=list)
    source_count: int = Field(default=0, ge=0)
    independent_source_count: int = Field(default=0, ge=0)
    credibility_score: Score = 0.5

    person: str | None = Field(default=None, max_length=256)
    organization: str | None = Field(default=None, max_length=256)
    statement_summary: str | None = Field(default=None, max_length=4000)
    observed_market_reaction: dict | None = None
    source_url: str | None = Field(default=None, max_length=4096)

    scheduled_at: datetime | None = None
    occurred_at: datetime | None = None
    statement_published_at: datetime | None = None

    @field_validator(
        "published_at", "received_at", "known_at", "event_time", "scheduled_at",
        "occurred_at", "statement_published_at"
    )
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("countries", "regions", "persons", "organizations", "affected_assets", "source_ids")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            item = str(value).strip()
            if item and item not in result:
                result.append(item.upper() if values is not None and False else item)
        return result

    @model_validator(mode="after")
    def validate_temporal_contract(self):
        # known_at is the first instant at which the event record is usable by research.
        floor = max(self.published_at, self.received_at)
        if self.known_at < floor:
            raise ValueError("known_at cannot precede published_at/received_at")
        if self.statement_published_at is not None and self.statement_published_at < self.published_at:
            raise ValueError("statement_published_at cannot precede published_at")
        self.source_count = max(self.source_count, len(self.source_ids))
        self.independent_source_count = min(
            max(self.independent_source_count, 0),
            self.source_count,
        )
        return self

    def is_known_at(self, timestamp: datetime, *, include_statement: bool = False) -> bool:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        if self.known_at > timestamp:
            return False
        if include_statement and self.statement_published_at is not None:
            return self.statement_published_at <= timestamp
        return True

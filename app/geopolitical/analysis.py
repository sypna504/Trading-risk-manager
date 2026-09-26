from __future__ import annotations

from datetime import datetime

from .models import GeopoliticalEvent, GeopoliticalEventType, RiskDirection


def statement_event(
    *,
    event_id: str,
    person: str | None,
    organization: str | None,
    statement_summary: str,
    source_url: str,
    published_at: datetime,
    received_at: datetime,
    known_at: datetime,
    event_type: GeopoliticalEventType,
    crypto_relevance: float,
    source_id: str,
    countries: list[str] | None = None,
    affected_assets: list[str] | None = None,
    severity: float = 0.5,
    uncertainty: float = 0.5,
    direction: RiskDirection = RiskDirection.UNCERTAIN,
) -> GeopoliticalEvent:
    """Create a statement record without inferring motives or political ranking.

    The caller supplies the factual entities/category. This function only validates
    timing and stores the supplied neutral summary/evidence metadata.
    """
    return GeopoliticalEvent(
        event_id=event_id,
        event_type=event_type,
        published_at=published_at,
        received_at=received_at,
        known_at=known_at,
        event_time=published_at,
        countries=countries or [],
        persons=[person] if person else [],
        organizations=[organization] if organization else [],
        person=person,
        organization=organization,
        statement_summary=statement_summary,
        source_url=source_url,
        statement_published_at=published_at,
        severity=severity,
        uncertainty=uncertainty,
        crypto_relevance=crypto_relevance,
        risk_on_off_direction=direction,
        affected_assets=affected_assets or [],
        source_ids=[source_id],
        source_count=1,
        independent_source_count=1,
    )

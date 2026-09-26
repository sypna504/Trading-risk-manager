from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import GeopoliticalEvent, GeopoliticalEventType, RiskDirection


def geopolitical_features(events: list[GeopoliticalEvent], prediction_time: datetime) -> dict[str, float]:
    if prediction_time.tzinfo is None:
        prediction_time = prediction_time.replace(tzinfo=timezone.utc)
    prediction_time = prediction_time.astimezone(timezone.utc)
    known = [event for event in events if event.is_known_at(prediction_time)]
    last_24h = [event for event in known if event.known_at >= prediction_time - timedelta(hours=24)]

    def severity(types: set[GeopoliticalEventType]) -> float:
        values = [
            event.severity * event.crypto_relevance * event.credibility_score
            for event in last_24h if event.event_type in types
        ]
        return round(max(values, default=0.0), 4)

    risk_off = [
        event.severity * event.crypto_relevance
        for event in last_24h if event.risk_on_off_direction == RiskDirection.RISK_OFF
    ]
    scheduled = [
        event for event in known
        if event.scheduled_at is not None
        and prediction_time <= event.scheduled_at <= prediction_time + timedelta(hours=24)
        and event.known_at <= prediction_time
    ]
    return {
        "geo_event_count_24h": float(len(last_24h)),
        "geo_risk_off_score": round(max(risk_off, default=0.0), 4),
        "geo_conflict_score": severity({
            GeopoliticalEventType.ARMED_CONFLICT_ESCALATION,
            GeopoliticalEventType.ARMED_CONFLICT_DEESCALATION,
            GeopoliticalEventType.EMERGENCY_EVENT,
        }),
        "geo_sanctions_score": severity({
            GeopoliticalEventType.SANCTIONS,
            GeopoliticalEventType.TRADE_RESTRICTIONS,
            GeopoliticalEventType.TARIFFS,
        }),
        "geo_macro_score": severity({
            GeopoliticalEventType.CENTRAL_BANK_STATEMENT,
            GeopoliticalEventType.MACRO_RELEASE,
            GeopoliticalEventType.BANKING_CRISIS,
            GeopoliticalEventType.SOVEREIGN_RISK,
        }),
        "scheduled_event_24h": float(bool(scheduled)),
    }

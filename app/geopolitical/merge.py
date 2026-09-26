from __future__ import annotations

from datetime import timedelta

from .models import GeopoliticalEvent


def merge_event_sources(events: list[GeopoliticalEvent], *, tolerance: timedelta = timedelta(hours=1)) -> list[GeopoliticalEvent]:
    """Merge source-level records for the same event without inventing facts."""
    merged: list[GeopoliticalEvent] = []
    for event in sorted(events, key=lambda item: (item.event_time or item.known_at, item.known_at)):
        match_index = None
        for index, existing in enumerate(merged):
            existing_time = existing.event_time or existing.known_at
            event_time = event.event_time or event.known_at
            same_type = existing.event_type == event.event_type
            time_close = abs(existing_time - event_time) <= tolerance
            same_country = bool(set(existing.countries) & set(event.countries)) or (not existing.countries and not event.countries)
            if same_type and time_close and same_country:
                match_index = index
                break
        if match_index is None:
            merged.append(event)
            continue
        existing = merged[match_index]
        source_ids = list(dict.fromkeys([*existing.source_ids, *event.source_ids]))
        countries = list(dict.fromkeys([*existing.countries, *event.countries]))
        regions = list(dict.fromkeys([*existing.regions, *event.regions]))
        persons = list(dict.fromkeys([*existing.persons, *event.persons]))
        organizations = list(dict.fromkeys([*existing.organizations, *event.organizations]))
        affected_assets = list(dict.fromkeys([*existing.affected_assets, *event.affected_assets]))
        merged[match_index] = existing.model_copy(update={
            "source_ids": source_ids,
            "source_count": len(source_ids),
            "independent_source_count": len(source_ids),
            "countries": countries,
            "regions": regions,
            "persons": persons,
            "organizations": organizations,
            "affected_assets": affected_assets,
            "severity": max(existing.severity, event.severity),
            "crypto_relevance": max(existing.crypto_relevance, event.crypto_relevance),
            "credibility_score": max(existing.credibility_score, event.credibility_score),
            "uncertainty": min(existing.uncertainty, event.uncertainty),
            "known_at": max(existing.known_at, event.known_at),
        })
    return merged

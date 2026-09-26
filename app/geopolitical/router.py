from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.geopolitical.models import GeopoliticalEvent
from app.geopolitical.repository import GeopoliticalEventRepository

from app.backend.api.app.config import settings

router = APIRouter(prefix="/events", tags=["events"])
repository = GeopoliticalEventRepository(settings.DATABASE_PATH)


@router.get("", response_model=list[GeopoliticalEvent])
def list_events(limit: int = Query(default=100, ge=1, le=500)):
    return repository.list_recent(limit)


@router.get("/{event_id}", response_model=GeopoliticalEvent)
def get_event(event_id: str):
    event = repository.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return event

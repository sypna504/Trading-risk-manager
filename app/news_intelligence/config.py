from __future__ import annotations

from pydantic import BaseModel, Field


class NewsSettings(BaseModel):
    """Small deterministic configuration for MVP-1 news context."""

    high_impact_probability: float = Field(default=0.70, ge=0.0, le=1.0)
    high_relevance: float = Field(default=0.60, ge=0.0, le=1.0)
    default_language: str = "en"
    default_list_limit: int = Field(default=100, ge=1, le=500)


settings = NewsSettings()

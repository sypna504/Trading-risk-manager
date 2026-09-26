from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceKind(str, Enum):
    FACT = "fact"
    MODEL_ESTIMATE = "model_estimate"
    NEWS_CLASSIFICATION = "news_classification"
    CORRELATION = "correlation"
    UNCERTAIN_INTERPRETATION = "uncertain_interpretation"


class AgentQueryRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class EvidenceItem(BaseModel):
    kind: EvidenceKind
    source: str
    record_id: str | None = None
    url: str | None = None
    timestamp: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class AgentQueryResponse(BaseModel):
    answer: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainty: float = Field(ge=0, le=1)
    model_used: str
    degraded: bool = False

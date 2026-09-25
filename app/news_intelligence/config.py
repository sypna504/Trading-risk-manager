from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class NewsSettings(BaseModel):
    high_impact_probability: float = Field(default=0.70, ge=0.0, le=1.0)
    high_relevance: float = Field(default=0.60, ge=0.0, le=1.0)
    default_language: str = "en"
    default_list_limit: int = Field(default=100, ge=1, le=500)


class TelegramSettings(BaseModel):
    api_id: int | None = None
    api_hash: str | None = None
    session_path: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_id and self.api_hash and self.session_path)

    @classmethod
    def from_env(cls) -> "TelegramSettings":
        raw_api_id = os.getenv("TELEGRAM_API_ID", "").strip()
        try:
            api_id = int(raw_api_id) if raw_api_id else None
        except ValueError:
            api_id = None
        return cls(
            api_id=api_id,
            api_hash=os.getenv("TELEGRAM_API_HASH", "").strip() or None,
            session_path=os.getenv("TELEGRAM_SESSION_PATH", "").strip() or None,
        )


class LocalLLMSettings(BaseModel):
    provider: str = "rule_based"
    url: str = "http://ollama:11434"
    model: str | None = None
    timeout_seconds: float = Field(default=8.0, gt=0.0, le=120.0)

    @classmethod
    def from_env(cls) -> "LocalLLMSettings":
        raw_timeout = os.getenv("NEWS_LLM_TIMEOUT_SECONDS", "8").strip()
        try:
            timeout = float(raw_timeout)
        except ValueError:
            timeout = 8.0
        return cls(
            provider=os.getenv("NEWS_LLM_PROVIDER", "rule_based").strip().lower() or "rule_based",
            url=os.getenv("NEWS_LLM_URL", "http://ollama:11434").strip() or "http://ollama:11434",
            model=os.getenv("NEWS_LLM_MODEL", "").strip() or None,
            timeout_seconds=timeout,
        )


class SourceConfigPaths(BaseModel):
    news_sources: Path = Path("config/news_sources.yaml")


settings = NewsSettings()

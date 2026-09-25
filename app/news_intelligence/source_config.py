from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class TelegramSourceConfig(BaseModel):
    enabled: bool = False
    channels: list[str] = Field(default_factory=list)


class RSSSourceConfig(BaseModel):
    enabled: bool = True
    sources: list[Any] = Field(default_factory=list)


class NewsSourcesConfig(BaseModel):
    telegram: TelegramSourceConfig = Field(default_factory=TelegramSourceConfig)
    rss: RSSSourceConfig = Field(default_factory=RSSSourceConfig)


def load_news_sources_config(path: str | Path = "config/news_sources.yaml") -> NewsSourcesConfig:
    config_path = Path(path)
    if not config_path.exists():
        return NewsSourcesConfig()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return NewsSourcesConfig.model_validate(payload)

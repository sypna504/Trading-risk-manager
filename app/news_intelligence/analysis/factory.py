from __future__ import annotations

from .base import NewsAnalyzer
from .local_llm import LocalLLMNewsAnalyzer
from .rule_based import RuleBasedNewsAnalyzer
from ..config import LocalLLMSettings


def build_news_analyzer_from_env() -> NewsAnalyzer:
    config = LocalLLMSettings.from_env()
    fallback = RuleBasedNewsAnalyzer()
    if config.provider == "ollama":
        return LocalLLMNewsAnalyzer(
            base_url=config.url,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
            fallback=fallback,
        )
    return fallback

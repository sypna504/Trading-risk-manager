from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen

from pydantic import ValidationError

from .base import NewsAnalyzer
from .rule_based import RuleBasedNewsAnalyzer
from ..config import LocalLLMSettings
from ..models import NewsAnalysisResult, NewsItem


logger = logging.getLogger(__name__)
Transport = Callable[[str, dict[str, Any], float], dict[str, Any]]


def _ollama_transport(base_url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/generate"
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured local Ollama URL
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Ollama response must be a JSON object")
    return parsed


class LocalLLMNewsAnalyzer(NewsAnalyzer):
    """Ollama adapter with strict structured validation and rule fallback."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str | None,
        timeout_seconds: float = 8.0,
        fallback: NewsAnalyzer | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url
        self.model = (model or "").strip() or None
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback or RuleBasedNewsAnalyzer()
        self.transport = transport or _ollama_transport

    @classmethod
    def from_env(cls, *, fallback: NewsAnalyzer | None = None) -> "LocalLLMNewsAnalyzer":
        config = LocalLLMSettings.from_env()
        return cls(
            base_url=config.url,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
            fallback=fallback,
        )

    @staticmethod
    def _prompt(text: str) -> str:
        return (
            "Analyze only the NEWS_TEXT below. Do not invent facts that are not explicitly present. "
            "Do not output source, URL, publication time, quotes, prices, or extra events. "
            "If evidence is weak, use neutral/other/uncertain and increase uncertainty. "
            "Return JSON only with exactly these fields: "
            "sentiment, event_type, crypto_relevance, impact_direction, impact_probability, "
            "affected_assets, uncertainty. "
            "Allowed sentiment: negative, neutral, positive. "
            "Allowed event_type: regulation, etf, exchange, hack, stablecoin, macro, geopolitical, "
            "token_specific, other. Allowed impact_direction: bullish, bearish, uncertain. "
            "All numeric scores must be in [0,1]. affected_assets must be a JSON array of ticker strings.\n"
            f"NEWS_TEXT:\n{text}"
        )

    def _fallback(self, item: NewsItem, reason: str) -> NewsItem:
        logger.warning("local news LLM fallback: %s", reason)
        return self.fallback.analyze(item)

    def analyze(self, item: NewsItem) -> NewsItem:
        if not self.model:
            return self._fallback(item, "NEWS_LLM_MODEL is not configured")
        text = item.text.strip()
        if not text:
            return self._fallback(item, "NewsItem.text is empty")

        payload = {
            "model": self.model,
            "prompt": self._prompt(text),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        try:
            response = self.transport(self.base_url, payload, self.timeout_seconds)
            raw = response.get("response")
            if not isinstance(raw, str) or not raw.strip():
                return self._fallback(item, "empty Ollama response")
            result = NewsAnalysisResult.model_validate_json(raw)
        except (ValidationError, ValueError, TypeError, TimeoutError, OSError, json.JSONDecodeError) as error:
            return self._fallback(item, f"{type(error).__name__}: {error}")
        except Exception as error:  # adapter must not break ingestion on provider failures
            return self._fallback(item, f"{type(error).__name__}: {error}")

        return item.model_copy(
            update={
                "sentiment": result.sentiment,
                "event_type": result.event_type,
                "crypto_relevance": result.crypto_relevance,
                "impact_direction": result.impact_direction,
                "impact_probability": result.impact_probability,
                "crypto_assets": result.affected_assets,
                "uncertainty": result.uncertainty,
            }
        )

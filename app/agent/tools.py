from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ReadOnlyAnalyticsTools:
    """Read-only facade. No method mutates thresholds, models, risk or portfolios."""

    ALLOWED = {
        "get_market_snapshot", "get_active_model", "get_model_metrics",
        "get_recent_predictions", "get_decision", "get_recent_news",
        "get_news_for_symbol", "get_high_impact_events", "get_geopolitical_events",
        "get_event_reaction", "get_outcome_metrics", "get_false_positives",
        "get_false_negatives", "get_backtest_summary", "get_research_summary",
        "get_paper_portfolio", "get_system_health",
    }

    def __init__(self, providers: dict[str, Callable[..., Any]] | None = None) -> None:
        self.providers = dict(providers or {})
        forbidden = set(self.providers) - self.ALLOWED
        if forbidden:
            raise ValueError(f"forbidden agent tools: {sorted(forbidden)}")

    def call(self, name: str, **kwargs):
        if name not in self.ALLOWED:
            raise PermissionError(f"tool is not read-only or not allowed: {name}")
        provider = self.providers.get(name)
        if provider is None:
            return None
        return provider(**kwargs)

    def available(self) -> list[str]:
        return sorted(name for name in self.ALLOWED if name in self.providers)

    def __getattr__(self, name: str):
        if name in self.ALLOWED:
            return lambda **kwargs: self.call(name, **kwargs)
        raise AttributeError(name)

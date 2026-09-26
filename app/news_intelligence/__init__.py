"""Independent news-intelligence layer for informational crypto context.

MVP-3 exposes decision-time-safe market news context to the trading API.
The layer remains informational and does not change ``trade_allowed`` or
Quant Core thresholds/risk sizing.
"""

from .analysis import LocalLLMNewsAnalyzer, NewsAnalyzer, RuleBasedNewsAnalyzer
from .context import MarketNewsContextService
from .models import NewsAnalysisResult, NewsItem, NewsSource
from .service import NewsIntelligenceService
from .telegram import TelegramNewsSource

__all__ = [
    "MarketNewsContextService",
    "NewsItem",
    "NewsSource",
    "NewsAnalysisResult",
    "NewsAnalyzer",
    "RuleBasedNewsAnalyzer",
    "LocalLLMNewsAnalyzer",
    "TelegramNewsSource",
    "NewsIntelligenceService",
]

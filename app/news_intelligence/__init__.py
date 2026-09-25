"""Independent news-intelligence layer for informational crypto context.

MVP-2 adds optional Telegram ingestion and optional local Ollama analysis.
The layer still does not change ``trade_allowed`` or Quant Core thresholds.
"""

from .analysis import LocalLLMNewsAnalyzer, NewsAnalyzer, RuleBasedNewsAnalyzer
from .models import NewsAnalysisResult, NewsItem, NewsSource
from .service import NewsIntelligenceService
from .telegram import TelegramNewsSource

__all__ = [
    "NewsItem",
    "NewsSource",
    "NewsAnalysisResult",
    "NewsAnalyzer",
    "RuleBasedNewsAnalyzer",
    "LocalLLMNewsAnalyzer",
    "TelegramNewsSource",
    "NewsIntelligenceService",
]

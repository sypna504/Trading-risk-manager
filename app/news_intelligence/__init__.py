"""Independent news-intelligence layer for informational crypto context.

The module is intentionally isolated from trade-decision logic.  MVP-1 does
not change ``trade_allowed`` or any Quant Core threshold.
"""

from .models import NewsItem, NewsSource
from .service import NewsIntelligenceService

__all__ = ["NewsItem", "NewsSource", "NewsIntelligenceService"]

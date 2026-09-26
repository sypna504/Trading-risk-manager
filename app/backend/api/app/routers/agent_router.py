from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.agent.schemas import AgentQueryRequest, AgentQueryResponse
from app.agent.service import AnalyticalAgentService
from app.agent.tools import ReadOnlyAnalyticsTools
from app.geopolitical.repository import GeopoliticalEventRepository
from app.news_intelligence.storage import NewsRepository
from app.paper.repository import PaperRepository

from ..config import settings
from ..services.model_metadata_service import read_active_model_metadata
from ..storage.decision_repository import DecisionRepository

router = APIRouter(prefix="/agent", tags=["agent"])


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def _service() -> AnalyticalAgentService:
    decisions = DecisionRepository()
    news = NewsRepository(settings.DATABASE_PATH)
    events = GeopoliticalEventRepository(settings.DATABASE_PATH)
    paper = PaperRepository(settings.DATABASE_PATH)

    def recent() -> list[dict]:
        return decisions.list(limit=50)

    def latest_decision() -> dict | None:
        rows = recent()
        return rows[0] if rows else None

    def active_model() -> dict:
        try:
            metadata = read_active_model_metadata()
            config = metadata.get("config") or {}
            return {
                "model_version": metadata.get("model_version"),
                "model_status": config.get("model_status"),
                "feature_schema_version": config.get("feature_schema_version"),
                "supported_intervals": config.get("supported_intervals") or [],
                "data_age_hours": metadata.get("data_age_hours"),
            }
        except Exception as error:
            return {"available": False, "error": str(error)}

    def false_positives() -> list[dict]:
        return [
            row for row in decisions.list(limit=500)
            if row.get("outcome_status") == "completed"
            and row.get("trade_allowed") is True
            and row.get("actual_target") is False
        ][:50]

    def false_negatives() -> list[dict]:
        return [
            row for row in decisions.list(limit=500)
            if row.get("outcome_status") == "completed"
            and row.get("trade_allowed") is False
            and row.get("actual_target") is True
        ][:50]

    def recent_news() -> list[dict]:
        return [item.model_dump(mode="json") for item in news.list_news(limit=30)]

    def high_impact_news() -> list[dict]:
        return [
            item.model_dump(mode="json") for item in news.list_news(limit=100)
            if item.impact_probability >= 0.7 and item.crypto_relevance >= 0.5
        ][:30]

    providers = {
        "get_market_snapshot": latest_decision,
        "get_active_model": active_model,
        "get_model_metrics": lambda: _read_json(Path("runtime/research/FINAL_METRICS.json")),
        "get_recent_predictions": recent,
        "get_decision": latest_decision,
        "get_recent_news": recent_news,
        "get_news_for_symbol": lambda symbol="BTC": [
            item.model_dump(mode="json") for item in news.latest_for_symbol(symbol, limit=30)
        ],
        "get_high_impact_events": high_impact_news,
        "get_geopolitical_events": lambda: [
            item.model_dump(mode="json") for item in events.list_recent(30)
        ],
        "get_event_reaction": lambda: None,
        "get_outcome_metrics": decisions.outcome_summary,
        "get_false_positives": false_positives,
        "get_false_negatives": false_negatives,
        "get_backtest_summary": lambda: _read_json(Path("runtime/research/FINAL_METRICS.json")),
        "get_research_summary": lambda: _read_json(Path("runtime/research/LATEST.json")),
        "get_paper_portfolio": lambda: paper.get_portfolio().model_dump(mode="json") if paper.get_portfolio() else None,
        "get_system_health": lambda: {
            "backend": "available",
            "mode": "read-only",
            "real_trading": False,
        },
    }
    return AnalyticalAgentService(ReadOnlyAnalyticsTools(providers))


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(request: AgentQueryRequest):
    return _service().query(request.message)

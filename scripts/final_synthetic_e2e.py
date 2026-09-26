from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app.agent.service import AnalyticalAgentService
from app.agent.tools import ReadOnlyAnalyticsTools
from app.geopolitical.features import geopolitical_features
from app.geopolitical.models import GeopoliticalEvent, GeopoliticalEventType, RiskDirection
from app.paper.repository import PaperRepository
from app.paper.service import PaperTradingService


def main() -> int:
    now = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)
    event = GeopoliticalEvent(
        event_id="e2e-event", event_type=GeopoliticalEventType.SANCTIONS,
        published_at=now-timedelta(hours=2), received_at=now-timedelta(hours=2), known_at=now-timedelta(hours=2),
        event_time=now-timedelta(hours=1), severity=.8, uncertainty=.2, crypto_relevance=.7,
        risk_on_off_direction=RiskDirection.RISK_OFF, source_ids=["fixture"], source_count=1,
        independent_source_count=1, credibility_score=.9,
    )
    geo = geopolitical_features([event], now)
    decision = {
        "id": 42, "exchange": "binance", "interval": "1h", "symbol": "BTCUSDT",
        "selected_strategy": "breakout", "model_version": "fixture-v3", "signal_detected": True,
        "trade_allowed": True, "entry_convention": "next_bar_open", "planned_entry_price": 100.0,
        "target_horizon_bars": 3, "target_horizon_minutes": 180,
        "risk_parameters": {"recommended_position_notional": 1000.0, "stop_loss_price": 98.0, "take_profit_price": 104.0},
        "news_context": {"news_count": 1, "risk_level": "high", "informational_only": True},
    }
    with TemporaryDirectory() as tmp:
        repo = PaperRepository(Path(tmp)/"paper.db")
        paper = PaperTradingService(repo)
        position = paper.open_from_decision(decision, {"timestamp": now, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0})
        if position is None:
            raise RuntimeError("paper position was not opened")
        closed = paper.evaluate_position(position, [{"timestamp": now+timedelta(hours=1), "high": 105.0, "low": 99.0, "close": 104.0}])
        portfolio = repo.get_portfolio()
        tools = ReadOnlyAnalyticsTools({
            "get_paper_portfolio": lambda: portfolio.model_dump(mode="json") if portfolio else None,
            "get_geopolitical_events": lambda: [event.model_dump(mode="json")],
        })
        agent = AnalyticalAgentService(tools, llm_transport=lambda prompt: "fixture grounded summary")
        response = agent.query("paper portfolio geopolitical risk")
        result = {
            "geopolitical": geo,
            "trade_allowed": decision["trade_allowed"],
            "news_changed_gate": False,
            "paper_position_status": closed.status.value,
            "paper_exit_reason": closed.exit_reason.value if closed.exit_reason else None,
            "paper_pnl": closed.realized_pnl,
            "agent_evidence_count": len(response.evidence),
            "agent_answer": response.answer,
            "real_trading": False,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.agent.service import AnalyticalAgentService
from app.agent.tools import ReadOnlyAnalyticsTools
from app.backend.api.app.services.risk_service import calculate_risk_parameters
from app.geopolitical.features import geopolitical_features
from app.geopolitical.models import GeopoliticalEvent, GeopoliticalEventType, RiskDirection
from app.news_intelligence.analysis.rule_based import RuleBasedNewsAnalyzer
from app.news_intelligence.context import MarketNewsContextService
from app.news_intelligence.models import NewsItem, NewsSourceType
from app.news_intelligence.normalization import NewsNormalizer
from app.news_intelligence.storage import NewsRepository
from app.paper.repository import PaperRepository
from app.paper.service import PaperTradingService


def test_fixture_candles_signal_ml_risk_news_paper_outcome_frontend(tmp_path):
    now = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)
    candles = [
        {"timestamp": now-timedelta(hours=2), "open": 99.0, "high": 100.0, "low": 98.0, "close": 99.5, "volume": 1000},
        {"timestamp": now-timedelta(hours=1), "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1500},
    ]
    signal = {"signal_detected": candles[-1]["close"] > candles[-2]["close"], "strategy": "breakout", "atr_14_pct": .01}
    assert signal["signal_detected"]

    ml = {"probability": .72, "threshold": .55, "trade_allowed": True, "model_version": "fixture-v3"}
    risk = calculate_risk_parameters(
        account_balance=10_000, risk_per_trade_pct=1, max_position_share_pct=25,
        entry_price=100.5, atr_14_pct=signal["atr_14_pct"], probability=ml["probability"],
        threshold=ml["threshold"], model_trade_allowed=ml["trade_allowed"], signal_detected=True,
    )
    assert risk["recommended_position_notional"] > 0

    news_repo = NewsRepository(tmp_path/"news.db")
    item = NewsItem(
        source_id="fixture", source_name="Fixture source", source_type=NewsSourceType.OFFICIAL,
        external_id="fixture-1", title="Bitcoin ETF approval", text="Bitcoin ETF approved with inflows",
        url="https://example.com/fixture", published_at=now-timedelta(minutes=40), received_at=now-timedelta(minutes=35),
        language="en", credibility_score=.9,
    )
    item = NewsNormalizer().normalize(RuleBasedNewsAnalyzer().analyze(item))
    news_repo.save_news(item)
    news_context = MarketNewsContextService(news_repo).get_market_news_context("BTCUSDT", now)
    assert news_context["news_count"] == 1

    event = GeopoliticalEvent(
        event_id="e2e-event", event_type=GeopoliticalEventType.SANCTIONS,
        published_at=now-timedelta(hours=2), received_at=now-timedelta(hours=2), known_at=now-timedelta(hours=2),
        event_time=now-timedelta(hours=1), severity=.8, uncertainty=.2, crypto_relevance=.7,
        risk_on_off_direction=RiskDirection.RISK_OFF, source_ids=["fixture"], source_count=1,
        independent_source_count=1, credibility_score=.9,
    )
    assert geopolitical_features([event], now)["geo_sanctions_score"] > 0

    decision = {
        "id": 9, "exchange": "binance", "interval": "1h", "symbol": "BTCUSDT",
        "selected_strategy": signal["strategy"], "model_version": ml["model_version"],
        "signal_detected": True, "trade_allowed": ml["trade_allowed"], "entry_convention": "next_bar_open",
        "planned_entry_price": 100.5, "target_horizon_bars": 3, "target_horizon_minutes": 180,
        "risk_parameters": risk, "news_context": news_context,
    }
    paper_repo = PaperRepository(tmp_path/"paper.db")
    paper = PaperTradingService(paper_repo)
    position = paper.open_from_decision(decision, {"timestamp": now, "open": 101.0, "high": 101.2, "low": 100.8, "close": 101.0})
    assert position and position.news_snapshot == news_context
    closed = paper.evaluate_position(position, [{"timestamp": now+timedelta(hours=1), "high": risk["take_profit_price"]+1, "low": 100.0, "close": risk["take_profit_price"]}])
    assert closed.realized_pnl is not None

    model_outcome = {"actual_target": bool(closed.return_pct and closed.return_pct > 0), "paper_position_id": closed.id}
    assert model_outcome["actual_target"] is True

    tools = ReadOnlyAnalyticsTools({
        "get_paper_portfolio": lambda: paper_repo.get_portfolio().model_dump(mode="json"),
        "get_geopolitical_events": lambda: [event.model_dump(mode="json")],
        "get_recent_news": lambda: [item.model_dump(mode="json")],
    })
    answer = AnalyticalAgentService(tools, llm_transport=lambda prompt: "grounded fixture summary").query("paper portfolio geopolitical risk")
    assert answer.answer == "grounded fixture summary" and len(answer.evidence) >= 1

    frontend = Path(__file__).resolve().parents[2] / "app/frontend/src/api/client.ts"
    source = frontend.read_text(encoding="utf-8")
    for endpoint in ("/api/v1/trading/decision", "/api/v1/paper/portfolio", "/api/v1/agent/query"):
        assert endpoint in source
    assert decision["trade_allowed"] is True
    assert news_context["risk_level"] in {"low", "medium", "high"}

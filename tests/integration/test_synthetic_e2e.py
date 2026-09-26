from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
from fastapi.testclient import TestClient

from app.backend.api.app.main import app
from app.backend.api.app.routers import trade_decision_router
from app.backend.api.app.services import signal_service
from app.backend.api.app.services.market_services import Candle
from app.news_intelligence.context import MarketNewsContextService
from app.news_intelligence.ingestion import RSSNewsSource
from app.news_intelligence.models import NewsSource, NewsSourceType
from app.news_intelligence.service import NewsIntelligenceService
from app.news_intelligence.storage import NewsRepository


RSS = """<rss><channel>
<item><guid>fixture-etf-1</guid><title>Bitcoin ETF approved with strong inflows</title>
<description>Bitcoin ETF launch sees record inflow.</description>
<link>https://example.com/fixture-etf</link>
<pubDate>Fri, 25 Sep 2026 17:00:00 GMT</pubDate></item>
</channel></rss>"""


def _candles(count: int = 100) -> list[Candle]:
    start = datetime(2026, 9, 21, tzinfo=timezone.utc)
    return [
        Candle(
            timestamp=start + timedelta(hours=index),
            open=100.0,
            high=102.0,
            low=98.0,
            close=101.0,
            volume=1000.0,
        )
        for index in range(count)
    ]


def _compatibility():
    config = {
        "model_status": "validated",
        "feature_schema_version": "v3",
        "target_definition": "horizon_return_drawdown",
        "target_horizon_minutes": 180,
        "target_horizon_bars": 3,
        "supported_intervals": ["1h"],
        "calibration_method": "isotonic",
        "entry_convention": "next_bar_open",
        "exit_convention": "first_touch_tp_sl_then_timeout",
        "risk_atr_stop_multiplier": 1.5,
        "risk_min_stop_loss_pct": 0.5,
        "risk_reward_ratio": 2.0,
        "intrabar_priority": "stop_loss",
    }
    return SimpleNamespace(
        metadata={"model_version": "synthetic-v3"},
        config=config,
        warnings=(),
        model_version="synthetic-v3",
        model_status="validated",
    )


def test_synthetic_market_news_decision_frontend_flow(tmp_path, monkeypatch):
    now = datetime(2026, 9, 25, 18, 0, tzinfo=timezone.utc)

    repository = NewsRepository(tmp_path / "synthetic.db")
    source = NewsSource(
        id="fixture-rss",
        name="Fixture RSS",
        type=NewsSourceType.SPECIALIZED_CRYPTO,
        url="https://example.com/rss.xml",
        credibility_score=0.9,
    )
    adapter = RSSNewsSource(source, fetcher=lambda _url: RSS, clock=lambda: now)
    stored_news = NewsIntelligenceService(repository).ingest(adapter)
    assert len(stored_news) == 1

    context = MarketNewsContextService(repository).get_market_news_context("BTCUSDT", now)
    assert context["news_count"] == 1
    assert context["positive_count"] == 1
    assert context["top_events"][0]["event_type"] == "etf"

    feature_row = pd.DataFrame([{
        "timestamp": now - timedelta(hours=1),
        "symbol": "BTCUSDT",
        "close": 101.0,
        "atr_14_pct": 0.01,
        "rsi_14": 62.0,
        "price_z_20": 1.4,
        "volume_z_20": 1.2,
        "high_20": 100.5,
        "signal_breakout": 1,
        "signal_mean_reversion": 0,
        "trend_regime": "up",
        "volatility_regime": "normal",
    }])
    monkeypatch.setattr(signal_service, "calculate_features", lambda _frame: feature_row)
    signal = signal_service.detect_trading_signal(_candles(), "BTCUSDT", "1h")
    assert signal["signal_detected"] is True
    assert signal["active_strategies"] == ["breakout"]

    compatibility = _compatibility()
    monkeypatch.setattr(trade_decision_router, "_compatibility_or_http", lambda **_kwargs: compatibility)
    monkeypatch.setattr(trade_decision_router, "_download_candles", lambda *_args: _candles())
    monkeypatch.setattr(trade_decision_router, "detect_trading_signal", lambda *_args: signal)
    monkeypatch.setattr(
        trade_decision_router.trade_ml_client,
        "predict_quality",
        lambda **_kwargs: SimpleNamespace(
            prob_good_trade=0.72,
            raw_prob_good_trade=0.69,
            risk_score=0.28,
            trade_allowed=True,
            threshold=0.55,
            risk_level="low",
            model_version="synthetic-v3",
            calibration_method="isotonic",
        ),
    )
    monkeypatch.setattr(trade_decision_router, "_load_news_context", lambda *_args: context)

    captured: dict = {}

    def save_decision(payload):
        captured.update(payload)
        return 9001

    monkeypatch.setattr(trade_decision_router.repository, "save", save_decision)

    with TestClient(app) as client:
        response = client.get("/api/v1/trading/decision?symbol=BTCUSDT&interval=1h")
        assert response.status_code == 200
        decision = response.json()
        assert decision["trade_allowed"] is True
        assert decision["prob_good_trade"] == 0.72
        assert decision["threshold"] == 0.55
        assert decision["risk_parameters"]["recommended_position_notional"] > 0
        assert decision["news_context"]["news_count"] == 1
        assert captured["news_count"] == 1

        page = client.get("/")
        script = client.get("/static/app.js")
        assert page.status_code == 200
        assert script.status_code == 200
        assert "Trading Risk Manager" in page.text
        assert "/api/v1/trading/decision" in script.text
        assert "renderNewsContext" in script.text

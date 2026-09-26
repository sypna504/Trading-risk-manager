from __future__ import annotations

from app.backend.api.app.config import settings
from app.backend.api.app.storage.database import init_database
from app.backend.api.app.storage.decision_repository import DecisionRepository


def test_decision_news_snapshot_persists_without_touching_target(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "trading.db"))
    init_database()
    repository = DecisionRepository()
    decision_id = repository.save(
        {
            "created_at": "2026-09-25T18:00:00+00:00",
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "candles_count": 100,
            "signal_detected": True,
            "active_strategies": ["breakout"],
            "selected_strategy": "breakout",
            "probability": 0.7,
            "raw_probability": 0.7,
            "threshold": 0.5,
            "risk_score": 0.3,
            "risk_level": "low",
            "trade_allowed": True,
            "model_version": "risk_model_0208",
            "status": "evaluated",
            "reason": "test",
            "news_context_available": True,
            "news_risk_level": "high",
            "news_count": 4,
            "high_impact_news_count": 2,
            "target_definition": "horizon_return_drawdown",
            "target_horizon_minutes": 180,
            "target_horizon_bars": 3,
            "target_min_net_return": 0.002,
            "target_max_drawdown": -0.015,
            "target_fee": 0.001,
            "target_slippage": 0.0005,
        }
    )
    stored = repository.get(decision_id)
    assert stored["news_context_available"] is True
    assert stored["news_risk_level"] == "high"
    assert stored["news_count"] == 4
    assert stored["high_impact_news_count"] == 2
    assert stored["target_definition"] == "horizon_return_drawdown"
    assert stored["target_horizon_bars"] == 3

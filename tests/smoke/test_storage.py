from pathlib import Path

from app.backend.api.app.config import settings
from app.backend.api.app.storage.database import init_database
from app.backend.api.app.storage.decision_repository import DecisionRepository


def test_decision_is_saved(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "db.sqlite"))
    init_database()
    repository = DecisionRepository()

    decision_id = repository.save(
        {
            "created_at": "2026-08-02T12:00:00+00:00",
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "candles_count": 100,
            "signal_detected": False,
            "active_strategies": [],
            "selected_strategy": None,
            "probability": None,
            "threshold": None,
            "risk_score": None,
            "risk_level": None,
            "trade_allowed": False,
            "model_version": None,
            "entry_price": 100.0,
            "stop_loss_price": None,
            "take_profit_price": None,
            "position_size": 0.0,
            "position_notional": 0.0,
            "account_balance": 1000.0,
            "risk_per_trade_pct": 1.0,
            "status": "no_signal",
            "reason": "no signal",
        }
    )

    stored = repository.get(decision_id)
    assert stored["symbol"] == "BTCUSDT"
    assert stored["active_strategies"] == []
    assert stored["trade_allowed"] is False

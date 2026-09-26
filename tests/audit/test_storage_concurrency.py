from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.backend.api.app.config import settings
from app.backend.api.app.storage.database import init_database
from app.backend.api.app.storage.decision_repository import DecisionRepository


def _decision(index):
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
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
        "entry_price": 100 + index,
        "stop_loss_price": None,
        "take_profit_price": None,
        "position_size": 0,
        "position_notional": 0,
        "account_balance": 1000,
        "risk_per_trade_pct": 1,
        "status": "no_signal",
        "reason": "test",
    }


def test_concurrent_sqlite_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "decisions.db"))
    init_database()
    repository = DecisionRepository()
    with ThreadPoolExecutor(max_workers=8) as executor:
        ids = list(executor.map(lambda i: repository.save(_decision(i)), range(30)))
    assert len(set(ids)) == 30
    assert len(repository.list(limit=50)) == 30

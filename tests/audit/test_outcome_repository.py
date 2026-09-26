from datetime import datetime, timezone

from app.backend.api.app.config import settings
from app.backend.api.app.storage.database import init_database
from app.backend.api.app.storage.decision_repository import DecisionRepository


def _decision():
    return {
        "created_at": "2026-08-03T08:41:00+00:00",
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "candles_count": 100,
        "signal_detected": True,
        "active_strategies": ["mean_reversion"],
        "selected_strategy": "mean_reversion",
        "probability": 0.29,
        "threshold": 0.38,
        "risk_score": 0.71,
        "risk_level": "high",
        "trade_allowed": False,
        "model_version": "v1",
        "entry_price": 100,
        "stop_loss_price": 99,
        "take_profit_price": 102,
        "position_size": 0,
        "position_notional": 0,
        "account_balance": 1000,
        "risk_per_trade_pct": 1,
        "status": "evaluated",
        "reason": "test",
        "signal_timestamp": "2026-08-03T08:00:00+00:00",
        "outcome_due_at": "2026-08-03T12:00:00+00:00",
        "outcome_status": "pending",
        "target_horizon_bars": 3,
        "target_min_net_return": 0.002,
        "target_max_drawdown": -0.015,
    }


def test_repository_tracks_completed_false_negative(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "db.sqlite"))
    init_database()
    repository = DecisionRepository()
    decision_id = repository.save(_decision())

    due = repository.list_due_outcomes(
        now_iso="2026-08-03T12:01:00+00:00",
        limit=10,
    )
    assert [item["id"] for item in due] == [decision_id]

    repository.mark_outcome_completed(
        decision_id,
        {
            "outcome_checked_at": "2026-08-03T12:01:00+00:00",
            "realized_entry_price": 100,
            "realized_exit_price": 103,
            "realized_net_return": 0.027,
            "realized_max_drawdown": -0.005,
            "actual_target": True,
            "prediction_correct": False,
        },
    )

    stored = repository.get(decision_id)
    assert stored["outcome_status"] == "completed"
    assert stored["actual_target"] is True
    assert stored["prediction_correct"] is False

    summary = repository.outcome_summary()
    assert summary["false_negative"] == 1
    assert summary["incorrect"] == 1

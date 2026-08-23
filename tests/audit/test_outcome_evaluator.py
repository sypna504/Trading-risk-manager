from datetime import datetime, timezone

from app.backend.api.app.services.market_services import Candle
from app.backend.api.app.services.outcome_service import OutcomeEvaluator


class FakeRepository:
    def __init__(self):
        self.completed = []
        self.retries = []

    def list_due_outcomes(self, *, now_iso, limit):
        return [
            {
                "id": 1,
                "exchange": "binance",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "signal_timestamp": "2026-08-03T08:00:00+00:00",
                "target_horizon_bars": 3,
                "target_min_net_return": 0.002,
                "target_max_drawdown": -0.015,
                "trade_allowed": False,
            }
        ]

    def mark_outcome_completed(self, decision_id, outcome):
        self.completed.append((decision_id, outcome))

    def mark_outcome_retry(self, decision_id, *, checked_at, error):
        self.retries.append((decision_id, error))


def _candle(hour, open_, low, close):
    return Candle(
        timestamp=datetime(2026, 8, 3, hour, tzinfo=timezone.utc),
        open=open_,
        high=max(open_, close) + 1,
        low=low,
        close=close,
        volume=100,
    )


def test_evaluator_completes_due_decision(monkeypatch):
    repository = FakeRepository()
    evaluator = OutcomeEvaluator(repository)
    monkeypatch.setattr(
        evaluator,
        "_download",
        lambda _decision: [
            _candle(9, 100, 99.5, 101),
            _candle(10, 101, 100, 102),
            _candle(11, 102, 101, 103),
        ],
    )

    report = evaluator.run_once(
        now=datetime(2026, 8, 3, 12, 1, tzinfo=timezone.utc),
        limit=10,
    )

    assert report["completed"] == 1
    assert report["retries"] == 0
    assert repository.completed[0][0] == 1


def test_evaluator_marks_retry_when_data_is_not_ready(monkeypatch):
    repository = FakeRepository()
    evaluator = OutcomeEvaluator(repository)
    monkeypatch.setattr(
        evaluator,
        "_download",
        lambda _decision: [_candle(9, 100, 99, 100)],
    )

    report = evaluator.run_once(
        now=datetime(2026, 8, 3, 12, 1, tzinfo=timezone.utc),
        limit=10,
    )

    assert report["completed"] == 0
    assert report["retries"] == 1
    assert repository.retries

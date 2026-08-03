from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.backend.api.app.main import app
from app.backend.api.app.services.market_services import Candle
from app.backend.api.app.routers import trade_decision_router


def _candles(count=100):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            timestamp=start + timedelta(hours=index),
            open=100,
            high=102,
            low=98,
            close=101,
            volume=10,
        )
        for index in range(count)
    ]


def test_no_signal_response(monkeypatch):
    monkeypatch.setattr(
        trade_decision_router,
        "_download_candles",
        lambda *_args: _candles(),
    )
    monkeypatch.setattr(
        trade_decision_router,
        "detect_trading_signal",
        lambda *_args: {
            "signal_detected": False,
            "active_strategies": [],
            "timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "BTCUSDT",
            "close": 101.0,
            "atr_14_pct": 0.01,
            "signal_breakout": 0,
            "signal_mean_reversion": 0,
            "indicators": {},
            "reason": "no signal",
        },
    )
    monkeypatch.setattr(
        trade_decision_router.repository,
        "save",
        lambda _payload: 1,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/trading/decision")

    assert response.status_code == 200
    assert response.json()["status"] == "no_signal"
    assert response.json()["trade_allowed"] is False


def test_evaluated_response(monkeypatch):
    monkeypatch.setattr(
        trade_decision_router,
        "_download_candles",
        lambda *_args: _candles(),
    )
    monkeypatch.setattr(
        trade_decision_router,
        "detect_trading_signal",
        lambda *_args: {
            "signal_detected": True,
            "active_strategies": ["breakout"],
            "timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "BTCUSDT",
            "close": 101.0,
            "atr_14_pct": 0.01,
            "signal_breakout": 1,
            "signal_mean_reversion": 0,
            "indicators": {},
            "reason": "active signal: breakout",
        },
    )
    monkeypatch.setattr(
        trade_decision_router.trade_ml_client,
        "predict_quality",
        lambda **_kwargs: SimpleNamespace(
            prob_good_trade=0.7,
            risk_score=0.3,
            trade_allowed=True,
            threshold=0.5,
            risk_level="low",
            model_version="risk_model_0208",
        ),
    )
    monkeypatch.setattr(
        trade_decision_router.repository,
        "save",
        lambda _payload: 2,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/trading/decision")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "evaluated"
    assert payload["selected_strategy"] == "breakout"
    assert payload["risk_parameters"]["recommended_position_notional"] > 0

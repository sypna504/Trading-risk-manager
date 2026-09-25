from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.backend.api.app.routers import trade_decision_router
from app.backend.api.app.services.market_services import Candle


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


def _compatibility():
    config = {
        "model_status": "legacy_experimental",
        "feature_schema_version": "legacy_v2",
        "target_definition": "horizon_return_drawdown",
        "target_horizon_minutes": 180,
        "target_horizon_bars": 3,
        "target_min_net_return": 0.002,
        "target_max_drawdown": -0.015,
        "target_fee": 0.001,
        "target_slippage": 0.0005,
        "supported_intervals": ["1h"],
        "calibration_method": "none",
        "entry_convention": "next_bar_open",
        "exit_convention": "horizon_bar_close",
        "risk_atr_stop_multiplier": 1.5,
        "risk_min_stop_loss_pct": 0.5,
        "risk_reward_ratio": 2.0,
        "intrabar_priority": "stop_loss",
    }
    return SimpleNamespace(
        metadata={"model_version": "risk_model_0208"},
        config=config,
        warnings=(),
        model_version="risk_model_0208",
        model_status="legacy_experimental",
    )


def _prediction():
    return SimpleNamespace(
        prob_good_trade=0.7,
        raw_prob_good_trade=0.7,
        risk_score=0.3,
        trade_allowed=True,
        threshold=0.5,
        risk_level="low",
        model_version="risk_model_0208",
        calibration_method="none",
    )


def _signal():
    return {
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
    }


def _context(*, risk_level="low", count=1, high_impact=0):
    return {
        "symbol": "BTCUSDT",
        "window_hours": 24,
        "news_count": count,
        "sentiment_score": 1.0 if count else 0.0,
        "positive_count": count,
        "negative_count": 0,
        "high_impact_count": high_impact,
        "geopolitical_risk_score": 0.0,
        "regulatory_risk_score": 0.0,
        "macro_risk_score": 0.0,
        "risk_level": risk_level,
        "top_events": [],
    }


def _prepare(monkeypatch, news_context):
    compatibility = _compatibility()
    monkeypatch.setattr(
        trade_decision_router,
        "_compatibility_or_http",
        lambda **_kwargs: compatibility,
    )
    monkeypatch.setattr(
        trade_decision_router,
        "_download_candles",
        lambda *_args: _candles(),
    )
    monkeypatch.setattr(
        trade_decision_router,
        "detect_trading_signal",
        lambda *_args: _signal(),
    )
    monkeypatch.setattr(
        trade_decision_router.trade_ml_client,
        "predict_quality",
        lambda **_kwargs: _prediction(),
    )
    monkeypatch.setattr(
        trade_decision_router,
        "_load_news_context",
        lambda *_args: news_context,
    )


def _decision():
    return trade_decision_router.get_trade_decision(
        exchange="binance",
        symbol="BTCUSDT",
        interval="1h",
        limit=100,
        account_balance=1000.0,
        risk_per_trade_pct=1.0,
        max_position_share_pct=25.0,
    )


def test_decision_works_when_news_unavailable(monkeypatch):
    _prepare(monkeypatch, None)
    monkeypatch.setattr(trade_decision_router.repository, "save", lambda _payload: 1)
    decision = _decision()
    assert decision.trade_allowed is True
    assert decision.news_context is None


def test_same_prediction_different_news_keeps_trade_gate_identical(monkeypatch):
    _prepare(monkeypatch, _context(risk_level="low", count=1))
    monkeypatch.setattr(trade_decision_router.repository, "save", lambda _payload: 1)
    positive = _decision()

    monkeypatch.setattr(
        trade_decision_router,
        "_load_news_context",
        lambda *_args: {
            **_context(risk_level="high", count=7, high_impact=5),
            "sentiment_score": -1.0,
            "positive_count": 0,
            "negative_count": 7,
            "regulatory_risk_score": 0.95,
        },
    )
    negative = _decision()

    assert positive.trade_allowed == negative.trade_allowed
    assert positive.prob_good_trade == negative.prob_good_trade
    assert positive.threshold == negative.threshold
    assert positive.risk_parameters == negative.risk_parameters


def test_news_snapshot_is_persisted(monkeypatch):
    context = _context(risk_level="high", count=4, high_impact=2)
    _prepare(monkeypatch, context)
    saved = {}

    def capture(payload):
        saved.update(payload)
        return 9

    monkeypatch.setattr(trade_decision_router.repository, "save", capture)
    decision = _decision()
    assert decision.id == 9
    assert saved["news_context_available"] is True
    assert saved["news_risk_level"] == "high"
    assert saved["news_count"] == 4
    assert saved["high_impact_news_count"] == 2


def test_reason_marks_news_as_informational(monkeypatch):
    _prepare(monkeypatch, _context(risk_level="low", count=1))
    monkeypatch.setattr(trade_decision_router.repository, "save", lambda _payload: 1)
    decision = _decision()
    assert "news layer is informational and does not alter the ML trading gate" in decision.reason

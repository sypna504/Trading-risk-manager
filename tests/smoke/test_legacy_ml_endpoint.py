from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.backend.api.app.main import app
from app.backend.api.app.routers import ml_service_router
from app.backend.api.app.services.market_services import Candle, Candles


def test_legacy_prediction_endpoint(monkeypatch):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = Candles(
        symbol="BTC/USDT",
        interval="1h",
        items=[
            Candle(
                timestamp=start + timedelta(hours=index),
                open=100,
                high=102,
                low=98,
                close=101,
                volume=10,
            )
            for index in range(60)
        ],
    )

    class FakeDownloader:
        def __init__(self, **_kwargs):
            pass

        def get_binance_candles(self):
            return candles

        def get_bybit_candles_dc(self):
            return candles

    monkeypatch.setattr(ml_service_router, "GetCandles", FakeDownloader)
    monkeypatch.setattr(
        ml_service_router.ml_client,
        "predict_quality",
        lambda **_kwargs: SimpleNamespace(
            prob_good_trade=0.6,
            risk_score=0.4,
            trade_allowed=True,
            threshold=0.5,
            risk_level="medium",
            model_version="risk_model_0208",
        ),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ml/prediction-quality",
            params={"limit": 60},
        )

    assert response.status_code == 200
    assert response.json()["model_version"] == "risk_model_0208"

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

from app.backend.api.app.grpc_client import MLGrpcClient
from app.backend.api.app.services.market_services import Candle


def _candles(rows: int = 320) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    for index in range(rows):
        close = 100.0 + 0.03 * index + 2.0 * math.sin(index / 9.0)
        open_price = close - 0.1 * math.cos(index / 6.0)
        candles.append(
            Candle(
                timestamp=start + timedelta(hours=index),
                open=open_price,
                high=max(open_price, close) + 0.5,
                low=min(open_price, close) - 0.5,
                close=close,
                volume=1200.0 + index * 3.0 + 70.0 * (1 + math.sin(index / 8.0)),
            )
        )
    return candles


def main() -> int:
    client = MLGrpcClient()
    try:
        response = client.predict_quality(
            symbol="BTCUSDT",
            interval="1h",
            strategy_name="mean_reversion",
            candles=_candles(),
            timeout=30,
        )
        payload = {
            "prob_good_trade": response.prob_good_trade,
            "raw_prob_good_trade": response.raw_prob_good_trade,
            "risk_score": response.risk_score,
            "trade_allowed": response.trade_allowed,
            "threshold": response.threshold,
            "risk_level": response.risk_level,
            "model_version": response.model_version,
            "calibration_method": response.calibration_method,
            "probability_bin": response.probability_bin,
            "model_supported_interval": response.model_supported_interval,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import math
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import numpy as np
from ml.v1 import ml_pb2

from app.backend.api.app.config import settings
from app.backend.api.app.schemas.ml_schemas import MLpredictresponse, ModelInfoResponse
from app.backend.api.app.services.market_services import Candle
from app.backend.api.app.services.signal_service import detect_trading_signal


def _candles(rows: int = 320) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result: list[Candle] = []
    for index in range(rows):
        close = 100.0 + 0.025 * index + 1.8 * math.sin(index / 8.0)
        open_price = close - 0.08 * math.cos(index / 5.0)
        high = max(open_price, close) + 0.48
        low = min(open_price, close) - 0.48
        volume = 1100.0 + 2.0 * index + 60.0 * (1.0 + math.sin(index / 7.0))
        result.append(
            Candle(
                timestamp=start + timedelta(hours=index),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return result


def _run(name: str, fn: Callable[[], Any], results: dict[str, Any]) -> None:
    try:
        results[name] = {"ok": True, "value": fn()}
    except Exception as error:
        results[name] = {
            "ok": False,
            "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        }


def _static_contract() -> dict[str, Any]:
    fields = ml_pb2.PredictSignalQualityResponse.DESCRIPTOR.fields_by_name
    expected = {
        "prob_good_trade",
        "raw_prob_good_trade",
        "risk_score",
        "trade_allowed",
        "threshold",
        "risk_level",
        "model_version",
        "calibration_method",
        "probability_bin",
        "model_supported_interval",
    }
    missing = sorted(expected - set(fields))
    if missing:
        raise AssertionError(f"backend protobuf is stale; missing={missing}")
    if not hasattr(settings, "MIN_CANDLES"):
        raise AssertionError("backend settings has no MIN_CANDLES")
    if int(settings.MIN_CANDLES) != 60:
        raise AssertionError(f"backend MIN_CANDLES={settings.MIN_CANDLES}, expected 60")
    MLpredictresponse.model_json_schema()
    ModelInfoResponse.model_json_schema()
    return {
        "min_candles": int(settings.MIN_CANDLES),
        "proto_fields": sorted(fields),
    }


def _signal_contract() -> dict[str, Any]:
    result = detect_trading_signal(_candles(), "BTCUSDT", interval="1h")
    required = {
        "signal_detected",
        "active_strategies",
        "timestamp",
        "symbol",
        "close",
        "atr_14_pct",
        "signal_breakout",
        "signal_mean_reversion",
        "indicators",
        "reason",
    }
    missing = sorted(required - set(result))
    if missing:
        raise AssertionError(f"signal result fields are missing: {missing}")
    return result


def main() -> int:
    results: dict[str, Any] = {}
    _run("static_contract", _static_contract, results)
    _run("signal_contract", _signal_contract, results)
    ok = all(item.get("ok") for item in results.values())
    print(json.dumps({"ok": ok, "checks": results}, ensure_ascii=False, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

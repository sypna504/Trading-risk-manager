from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .models import GeopoliticalEvent

PRE_HOURS = (-24, -6, -1)
POST_HOURS = (1, 3, 6, 12, 24, 72)


def _nearest(part: pd.DataFrame, timestamp: pd.Timestamp) -> pd.Series | None:
    eligible = part[part["timestamp"] <= timestamp]
    if eligible.empty:
        return None
    return eligible.iloc[-1]


def _period_metrics(part: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float | None]:
    window = part[(part["timestamp"] >= start) & (part["timestamp"] <= end)].copy()
    if window.empty:
        return {"return": None, "volume": None, "volatility": None, "mfe": None, "mae": None}
    first = float(window.iloc[0]["close"])
    last = float(window.iloc[-1]["close"])
    returns = window["close"].pct_change().dropna()
    return {
        "return": last / first - 1 if first else None,
        "volume": float(window["volume"].sum()),
        "volatility": float(returns.std()) if len(returns) > 1 else 0.0,
        "mfe": float(window["high"].max() / first - 1) if first else None,
        "mae": float(window["low"].min() / first - 1) if first else None,
    }


def run_event_study(
    market: pd.DataFrame,
    event: GeopoliticalEvent,
    *,
    assets: Iterable[str] = ("BTCUSDT", "ETHUSDT"),
    benchmark_symbol: str = "BTCUSDT",
) -> dict[str, object]:
    if event.event_time is None:
        raise ValueError("event_time is required for event study")
    frame = market.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    event_time = pd.Timestamp(event.event_time)
    result: dict[str, object] = {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "event_time": event_time.isoformat(),
        "causal_claim": False,
        "language": "observed after/before event; no causal identification",
        "assets": {},
    }

    benchmark = frame[frame["symbol"] == benchmark_symbol].sort_values("timestamp")
    for asset in assets:
        part = frame[frame["symbol"] == asset].sort_values("timestamp")
        windows: dict[str, object] = {}
        for hours in PRE_HOURS:
            start, end = event_time + pd.Timedelta(hours=hours), event_time
            metrics = _period_metrics(part, start, end)
            bench = _period_metrics(benchmark, start, end)
            metrics["benchmark_adjusted_return"] = (
                metrics["return"] - bench["return"]
                if metrics["return"] is not None and bench["return"] is not None else None
            )
            windows[f"{hours}h_to_event"] = metrics
        for hours in POST_HOURS:
            start, end = event_time, event_time + pd.Timedelta(hours=hours)
            metrics = _period_metrics(part, start, end)
            bench = _period_metrics(benchmark, start, end)
            metrics["benchmark_adjusted_return"] = (
                metrics["return"] - bench["return"]
                if metrics["return"] is not None and bench["return"] is not None else None
            )
            windows[f"event_to_{hours}h"] = metrics
        result["assets"][asset] = windows
    return result

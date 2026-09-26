from __future__ import annotations

import json
from datetime import timedelta

import numpy as np
import pandas as pd

from app.geopolitical.models import GeopoliticalEvent, GeopoliticalEventType, RiskDirection
from app.geopolitical.research import compare_geopolitical_features


def main() -> int:
    timestamps = pd.date_range("2026-01-01", periods=160, freq="h", tz="UTC")
    x = np.sin(np.arange(len(timestamps)) / 8)
    target = (x > 0).astype(int)
    market = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "BTCUSDT",
        "price_feature": x + np.random.default_rng(42).normal(0, .15, len(x)),
        "target_good_trade": target,
    })
    events = []
    for i in range(12, 145, 16):
        ts = timestamps[i].to_pydatetime()
        events.append(GeopoliticalEvent(
            event_id=f"fixture-{i}",
            event_type=GeopoliticalEventType.SANCTIONS if target[i] == 0 else GeopoliticalEventType.DIPLOMATIC_MEETING,
            published_at=ts - timedelta(minutes=30), received_at=ts - timedelta(minutes=20), known_at=ts - timedelta(minutes=20),
            event_time=ts, severity=.8, uncertainty=.2, crypto_relevance=.7,
            risk_on_off_direction=RiskDirection.RISK_OFF if target[i] == 0 else RiskDirection.RISK_ON,
            source_ids=[f"s{i}"], source_count=1, independent_source_count=1, credibility_score=.8,
        ))
    report = compare_geopolitical_features(market, events, base_features=["price_feature"])
    report["evidence_scope"] = "synthetic_only"
    report["geopolitical_improvement_proven"] = False
    report["production_gate_change"] = False
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml_services.app.research.news_fusion import (
    merge_market_news_features,
    run_news_fusion_research,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runtime" / "news_fusion_synthetic.json"


def fixture_market(rows: int = 720) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    rng = np.random.default_rng(504)
    momentum = np.sin(np.arange(rows) / 13.0) + rng.normal(0, 0.30, rows)
    volatility = 0.5 + np.abs(np.cos(np.arange(rows) / 31.0))
    latent = 0.85 * momentum - 0.35 * volatility + rng.normal(0, 0.55, rows)
    target = (latent > np.median(latent)).astype(int)
    net_return = np.where(target == 1, 0.008, -0.005) + rng.normal(0, 0.002, rows)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": "BTCUSDT",
            "price_momentum": momentum,
            "price_volatility": volatility,
            "target_good_trade": target,
            "net_return": net_return,
        }
    )


def fixture_news(market: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for index in range(18, len(market), 9):
        timestamp = market.iloc[index]["timestamp"] - pd.Timedelta(minutes=20)
        target = int(market.iloc[index]["target_good_trade"])
        rows.append(
            {
                "id": f"n-{index}",
                "source_id": f"source-{index % 4}",
                "source_name": "synthetic",
                "published_at": timestamp,
                "received_at": timestamp + pd.Timedelta(minutes=2),
                "crypto_assets": ["BTC"],
                "event_type": "etf" if target else "regulation",
                "sentiment": "positive" if target else "negative",
                "impact_direction": "bullish" if target else "bearish",
                "crypto_relevance": 0.95,
                "impact_probability": 0.80,
                "credibility_score": 0.90,
                "uncertainty": 0.20,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    market = fixture_market()
    news = fixture_news(market)
    merged = merge_market_news_features(market, news)
    report = run_news_fusion_research(
        merged,
        price_features=["price_momentum", "price_volatility"],
        seeds=(42, 137, 271),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml_services.app.research.news_fusion import (
    NEWS_FEATURE_COLUMNS,
    merge_market_news_features,
    run_news_fusion_research,
)


def market(rows: int = 80) -> pd.DataFrame:
    timestamp = pd.date_range("2026-09-20", periods=rows, freq="h", tz="UTC")
    x = np.linspace(-1, 1, rows)
    target = (x + 0.2 * np.sin(np.arange(rows)) > 0).astype(int)
    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "symbol": "BTCUSDT",
            "p1": x,
            "p2": np.cos(np.arange(rows) / 4),
            "target_good_trade": target,
            "net_return": np.where(target, 0.01, -0.006),
        }
    )


def item(**overrides):
    payload = {
        "id": "n1",
        "source_id": "source-a",
        "source_name": "source",
        "published_at": pd.Timestamp("2026-09-21T00:00:00Z"),
        "received_at": pd.Timestamp("2026-09-21T00:01:00Z"),
        "crypto_assets": ["BTC"],
        "event_type": "regulation",
        "sentiment": "negative",
        "impact_direction": "bearish",
        "crypto_relevance": 0.9,
        "impact_probability": 0.9,
        "credibility_score": 0.9,
        "uncertainty": 0.2,
    }
    payload.update(overrides)
    return payload


def test_future_news_excluded():
    m = market(2)
    future = pd.DataFrame([item(published_at=m.iloc[0].timestamp + pd.Timedelta(minutes=1), received_at=m.iloc[0].timestamp + pd.Timedelta(minutes=1))])
    merged = merge_market_news_features(m, future)
    assert merged.iloc[0].news_count_24h == 0


def test_article_arriving_late_is_not_backfilled():
    m = market(4)
    published = m.iloc[0].timestamp - pd.Timedelta(hours=1)
    news = pd.DataFrame([item(published_at=published, received_at=m.iloc[2].timestamp + pd.Timedelta(minutes=1))])
    merged = merge_market_news_features(m, news)
    assert merged.iloc[0].news_count_24h == 0
    assert merged.iloc[2].news_count_24h == 0
    assert merged.iloc[3].news_count_24h == 1


def test_future_edit_is_not_backfilled():
    m = market(5)
    news = pd.DataFrame([item(
        published_at=m.iloc[0].timestamp - pd.Timedelta(hours=1),
        received_at=m.iloc[0].timestamp - pd.Timedelta(minutes=50),
        edited_at=m.iloc[3].timestamp + pd.Timedelta(minutes=1),
    )])
    merged = merge_market_news_features(m, news)
    assert merged.iloc[2].news_count_24h == 0
    assert merged.iloc[4].news_count_24h == 1


def test_duplicate_news_does_not_inflate_event_count():
    m = market(30)
    ts = m.iloc[20].timestamp - pd.Timedelta(minutes=20)
    news = pd.DataFrame([
        item(id="a", source_id="s1", duplicate_group_id="g1", published_at=ts, received_at=ts),
        item(id="b", source_id="s2", duplicate_group_id="g1", published_at=ts, received_at=ts),
    ])
    merged = merge_market_news_features(m, news)
    row = merged.iloc[20]
    assert row.news_count_24h == 1
    assert row.independent_source_count == 2


def test_no_news_and_missing_news_service_have_neutral_features():
    m = market(3)
    a = merge_market_news_features(m, pd.DataFrame(columns=["published_at", "received_at"]))
    b = merge_market_news_features(m, None)
    assert a[NEWS_FEATURE_COLUMNS].equals(b[NEWS_FEATURE_COLUMNS])
    assert (a["news_count_24h"] == 0).all()


def test_timestamp_boundary_is_inclusive():
    m = market(2)
    ts = m.iloc[1].timestamp
    news = pd.DataFrame([item(published_at=ts, received_at=ts)])
    merged = merge_market_news_features(m, news)
    assert merged.iloc[1].news_count_24h == 1


def test_merge_correctness_and_asset_filter():
    m = market(30)
    ts = m.iloc[20].timestamp - pd.Timedelta(minutes=5)
    news = pd.DataFrame([
        item(id="btc", crypto_assets=["BTC"], published_at=ts, received_at=ts),
        item(id="eth", crypto_assets=["ETH"], event_type="token_specific", published_at=ts, received_at=ts),
    ])
    merged = merge_market_news_features(m, news)
    assert len(merged) == len(m)
    assert merged.iloc[20].news_count_24h == 1
    assert merged.iloc[20].asset_specific_news_score < 0


def test_price_only_reproducibility_when_news_changes():
    m = market(90)
    ts = m.iloc[40].timestamp - pd.Timedelta(minutes=5)
    negative = pd.DataFrame([item(published_at=ts, received_at=ts)])
    positive = pd.DataFrame([item(
        id="positive",
        published_at=ts,
        received_at=ts,
        sentiment="positive",
        impact_direction="bullish",
        event_type="etf",
    )])
    a = merge_market_news_features(m, negative)
    b = merge_market_news_features(m, positive)
    report_a = run_news_fusion_research(a, price_features=["p1", "p2"], seeds=(42,))
    report_b = run_news_fusion_research(b, price_features=["p1", "p2"], seeds=(42,))
    assert report_a["experiments"]["A_price_only"] == report_b["experiments"]["A_price_only"]
    assert report_a["experiments"]["G_news_context_only"] == report_a["experiments"]["A_price_only"]


def test_news_only_reproducibility():
    m = market(90)
    rows = []
    for i in range(10, 70, 8):
        ts = m.iloc[i].timestamp - pd.Timedelta(minutes=10)
        rows.append(item(
            id=f"n{i}",
            published_at=ts,
            received_at=ts,
            sentiment="positive" if i % 16 == 0 else "negative",
            impact_direction="bullish" if i % 16 == 0 else "bearish",
            event_type="etf" if i % 16 == 0 else "regulation",
        ))
    merged = merge_market_news_features(m, pd.DataFrame(rows))
    one = run_news_fusion_research(merged, price_features=["p1", "p2"], seeds=(42,))
    two = run_news_fusion_research(merged, price_features=["p1", "p2"], seeds=(42,))
    assert one["experiments"]["B_news_only"] == two["experiments"]["B_news_only"]


def test_final_holdout_is_after_all_selection_partitions():
    merged = merge_market_news_features(market(100), None)
    report = run_news_fusion_research(merged, price_features=["p1", "p2"], seeds=(42,))
    split = report["split"]
    assert split["train_end"] < split["meta_end"] < split["selection_end"] < split["final_start"]


def test_explicit_known_at_blocks_early_use():
    m = market(5)
    news = pd.DataFrame([item(
        published_at=m.iloc[0].timestamp - pd.Timedelta(hours=1),
        received_at=m.iloc[0].timestamp - pd.Timedelta(minutes=50),
        known_at=m.iloc[3].timestamp,
    )])
    merged = merge_market_news_features(m, news)
    assert merged.iloc[2].news_count_24h == 0
    assert merged.iloc[3].news_count_24h == 1


def test_synthetic_evidence_never_requests_production_gate_change():
    merged = merge_market_news_features(market(100), None)
    report = run_news_fusion_research(
        merged,
        price_features=["p1", "p2"],
        seeds=(42,),
        evidence_scope="research_only",
    )
    assert report["production_trade_gate_should_change"] is False
    assert report["news_improvement_proven"] is False


def test_price_features_may_include_categories():
    m = market(80)
    m["regime"] = np.where(np.arange(len(m)) % 2 == 0, "trend", "range")
    merged = merge_market_news_features(m, None)
    report = run_news_fusion_research(
        merged,
        price_features=["p1", "p2", "regime"],
        seeds=(42,),
    )
    assert np.isfinite(report["experiments"]["A_price_only"]["brier"])

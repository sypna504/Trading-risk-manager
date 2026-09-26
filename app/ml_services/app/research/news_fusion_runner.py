from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .news_fusion import merge_market_news_features, run_news_fusion_research


def _load_market(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        return pd.read_json(path)
    raise ValueError(f"unsupported market file: {path}")


def _load_news_sqlite(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["published_at", "received_at"])
    with sqlite3.connect(path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='news_items'"
        ).fetchone()
        if not exists:
            return pd.DataFrame(columns=["published_at", "received_at"])
        return pd.read_sql_query("SELECT * FROM news_items", connection)


def _load_news(path: Path | None, database: Path | None) -> pd.DataFrame:
    if path is not None:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in {".jsonl", ".ndjson"}:
            return pd.read_json(path, lines=True)
        if suffix == ".json":
            return pd.read_json(path)
        if suffix in {".parquet", ".pq"}:
            return pd.read_parquet(path)
        raise ValueError(f"unsupported news file: {path}")
    if database is not None:
        return _load_news_sqlite(database)
    return pd.DataFrame(columns=["published_at", "received_at"])


def _production_price_features(market: pd.DataFrame) -> list[str]:
    try:
        from ..features_builder import FEATURE_COLUMNS

        columns = [column for column in FEATURE_COLUMNS if column in market.columns]
    except Exception:
        columns = []
    if columns:
        return columns
    excluded = {
        "timestamp", "symbol", "strategy_name", "target_good_trade", "net_return",
        "entry_price", "exit_price", "max_drawdown",
    }
    return [
        column for column in market.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(market[column])
    ]


def _write_summary(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Leakage-safe price + news research runner")
    parser.add_argument("--market", type=Path, required=True, help="Market ML dataset CSV/JSONL/parquet")
    parser.add_argument("--news", type=Path, default=None, help="Historical news CSV/JSON/JSONL/parquet")
    parser.add_argument("--news-db", type=Path, default=None, help="SQLite database containing news_items")
    parser.add_argument("--output", type=Path, default=Path("runtime/news_fusion/report.json"))
    parser.add_argument("--price-features", default="", help="Comma-separated price feature columns")
    args = parser.parse_args()

    market = _load_market(args.market)
    news = _load_news(args.news, args.news_db)
    price_features = [value.strip() for value in args.price_features.split(",") if value.strip()]
    if not price_features:
        price_features = _production_price_features(market)
    if not price_features:
        raise SystemExit("no numeric price features found")

    merged = merge_market_news_features(market, news)
    report = run_news_fusion_research(
        merged,
        price_features=price_features,
        evidence_scope="research_only",
    )
    _write_summary(report, args.output)
    print(json.dumps({
        "output": str(args.output),
        "best_fusion_architecture": report["best_fusion_architecture"],
        "dataset_improvement_observed": report["dataset_improvement_observed"],
        "news_improvement_proven": report["news_improvement_proven"],
        "production_trade_gate_should_change": report["production_trade_gate_should_change"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

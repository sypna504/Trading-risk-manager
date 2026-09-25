from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.news_intelligence.analysis import RuleBasedNewsAnalyzer
from app.news_intelligence.normalization import NewsNormalizer
from app.news_intelligence.storage import NewsRepository


def analyzed(make_news_item, **kwargs):
    return RuleBasedNewsAnalyzer().analyze(NewsNormalizer().normalize(make_news_item(**kwargs)))


def test_storage_keeps_one_canonical_duplicate(tmp_path, make_news_item):
    repository = NewsRepository(tmp_path / "trading.db")
    first = analyzed(
        make_news_item,
        id="canonical",
        title="Bitcoin ETF approved",
        text="Strong inflows",
        url="https://example.com/a?utm_source=x",
    )
    second = analyzed(
        make_news_item,
        id="duplicate",
        title=" Bitcoin  ETF approved ",
        text="Strong inflows",
        url="https://EXAMPLE.com/a?utm_medium=y",
    )
    saved_first = repository.save_news(first)
    saved_second = repository.save_news(second)
    assert saved_first.id == "canonical"
    assert saved_second.id == "canonical"
    assert len(repository.list_news()) == 1


def test_symbol_filter_and_summary(tmp_path, make_news_item):
    repository = NewsRepository(tmp_path / "trading.db")
    now = datetime.now(timezone.utc)
    btc = analyzed(
        make_news_item,
        id="btc",
        title="Bitcoin ETF approved with record inflow",
        published_at=now - timedelta(hours=1),
        received_at=now - timedelta(minutes=50),
        external_id="btc",
        url="https://example.com/btc",
    )
    hack = analyzed(
        make_news_item,
        id="hack",
        title="Crypto exchange hacked and funds stolen",
        text="Major exploit affected users",
        published_at=now - timedelta(hours=2),
        received_at=now - timedelta(hours=2),
        external_id="hack",
        url="https://example.com/hack",
    )
    repository.save_news(btc)
    repository.save_news(hack)
    assert [item.id for item in repository.latest_for_symbol("BTC")] == ["btc"]
    summary = repository.summary(now=now)
    assert summary["last_24h_count"] == 2
    assert summary["positive"] == 1
    assert summary["negative"] == 1
    assert summary["high_impact"] >= 1
    assert summary["risk_level"] in {"low", "medium", "high"}


def test_news_table_does_not_modify_existing_decisions_table(tmp_path):
    import sqlite3

    path = tmp_path / "shared.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE decisions (id INTEGER PRIMARY KEY, marker TEXT NOT NULL)")
        connection.execute("INSERT INTO decisions(id, marker) VALUES (1, 'keep-me')")
        before = connection.execute("PRAGMA table_info(decisions)").fetchall()

    NewsRepository(path)

    with sqlite3.connect(path) as connection:
        after = connection.execute("PRAGMA table_info(decisions)").fetchall()
        marker = connection.execute("SELECT marker FROM decisions WHERE id = 1").fetchone()[0]
    assert after == before
    assert marker == "keep-me"

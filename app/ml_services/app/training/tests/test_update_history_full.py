from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from app.training import update_history as module
from app.training.training_config import TrainingConfig
from app.training.update_history import (
    _atomic_write_json,
    _atomic_write_parquet,
    _create_exchange,
    _fetch_symbol_history,
    _frame_hash,
    last_closed_open_time,
    merge_history,
    to_ccxt_symbol,
    update_history,
)


class FakeExchange:
    rateLimit = 0

    def __init__(self, pages=None, markets=None):
        self.pages = list(pages or [])
        self.markets = {"BTC/USDT": {}, "ETH/USDT": {}} if markets is None else markets
        self.loaded = False
        self.calls = []

    def load_markets(self):
        self.loaded = True
        return self.markets

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self.calls.append((symbol, timeframe, since, limit))
        return self.pages.pop(0) if self.pages else []


def _row(timestamp: str, symbol: str = "BTCUSDT", close: float = 100.0):
    return {
        "timestamp": pd.Timestamp(timestamp),
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": 10.0,
        "symbol": symbol,
    }


def test_to_ccxt_symbol_and_invalid():
    assert to_ccxt_symbol("btc/usdt") == "BTC/USDT"
    assert to_ccxt_symbol("ETH-USDC") == "ETH/USDC"
    with pytest.raises(ValueError, match="cannot convert"):
        to_ccxt_symbol("ABC")


def test_last_closed_open_time():
    result = last_closed_open_time(pd.Timestamp("2026-08-02T19:02:00Z"), "1h")
    assert result == pd.Timestamp("2026-08-02T18:00:00Z")


def test_create_exchange(monkeypatch, config):
    class ExchangeClass:
        def __init__(self, options):
            self.options = options

    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(binance=ExchangeClass))
    exchange = _create_exchange(config)
    assert exchange.options["enableRateLimit"] is True
    assert exchange.options["timeout"] == config.request_timeout * 1000

    config.exchange = "missing"
    with pytest.raises(ValueError, match="unsupported exchange"):
        _create_exchange(config)


def test_fetch_symbol_history_pages_and_cutoff(config):
    first = [
        [pd.Timestamp("2026-08-01T00:00:00Z").timestamp() * 1000, 1, 2, 0.5, 1.5, 10],
        [pd.Timestamp("2026-08-01T01:00:00Z").timestamp() * 1000, 1.5, 2, 1, 1.7, 11],
    ]
    second = [
        [pd.Timestamp("2026-08-01T02:00:00Z").timestamp() * 1000, 1.7, 2, 1.5, 1.8, 12],
    ]
    config.request_limit = 2
    exchange = FakeExchange(pages=[first, second])
    result = _fetch_symbol_history(
        exchange,
        "BTCUSDT",
        config,
        pd.Timestamp("2026-08-01T00:00:00Z"),
        pd.Timestamp("2026-08-01T02:00:00Z"),
    )
    assert len(result) == 3
    assert result["symbol"].unique().tolist() == ["BTCUSDT"]
    assert len(exchange.calls) == 2


def test_fetch_symbol_history_missing_market_and_empty(config):
    exchange = FakeExchange(markets={})
    with pytest.raises(ValueError, match="not available"):
        _fetch_symbol_history(
            exchange,
            "BTCUSDT",
            config,
            pd.Timestamp("2026-08-01T00:00:00Z"),
            pd.Timestamp("2026-08-01T02:00:00Z"),
        )

    exchange = FakeExchange(pages=[[]])
    result = _fetch_symbol_history(
        exchange,
        "BTCUSDT",
        config,
        pd.Timestamp("2026-08-01T00:00:00Z"),
        pd.Timestamp("2026-08-01T02:00:00Z"),
    )
    assert result.empty


def test_merge_history_and_frame_hash():
    old = pd.DataFrame([_row("2026-08-01T00:00:00Z", close=100)])
    new = pd.DataFrame([_row("2026-08-01T00:00:00Z", close=101)])
    merged = merge_history(old, new)
    assert len(merged) == 1
    assert merged.iloc[0]["close"] == 101
    assert _frame_hash(merged) == _frame_hash(merged.sample(frac=1))
    assert merge_history(pd.DataFrame(), pd.DataFrame()).empty


def test_atomic_write_json(tmp_path):
    path = tmp_path / "report.json"
    _atomic_write_json({"ok": True}, path)
    assert json.loads(path.read_text()) == {"ok": True}
    assert not path.with_suffix(".json.tmp").exists()


def test_atomic_write_parquet_uses_replace(monkeypatch, tmp_path):
    path = tmp_path / "history.parquet"

    def fake_to_parquet(self, target, index=False):
        Path(target).write_text("parquet-placeholder", encoding="utf-8")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)
    _atomic_write_parquet(pd.DataFrame({"x": [1]}), path)
    assert path.read_text() == "parquet-placeholder"


def _run_update_with_policy(monkeypatch, config, policy: str):
    config.symbols = ["BTCUSDT"]
    config.minimum_history_rows = 1
    config.history_symbol_policy = policy
    config.history_path.parent.mkdir(parents=True, exist_ok=True)
    config.history_path.write_bytes(b"placeholder")
    old = pd.DataFrame(
        [
            _row("2026-08-01T00:00:00Z", "BTCUSDT"),
            _row("2026-08-01T00:00:00Z", "CHZUSDT"),
        ]
    )
    monkeypatch.setattr(pd, "read_parquet", lambda *args, **kwargs: old.copy())
    stored = {}
    monkeypatch.setattr(module, "_atomic_write_parquet", lambda df, path: stored.setdefault("df", df.copy()))
    monkeypatch.setattr(module, "_atomic_write_json", lambda payload, path: stored.setdefault("report", payload))
    exchange = FakeExchange(pages=[[]], markets={"BTC/USDT": {}})
    result = update_history(
        config,
        exchange_factory=lambda _: exchange,
        now=pd.Timestamp("2026-08-01T03:05:00Z"),
    )
    return result, stored


def test_update_history_extend_accepts_existing_history_symbols(monkeypatch, config):
    result, stored = _run_update_with_policy(monkeypatch, config, "extend")
    assert result["history_only_symbols"] == ["CHZUSDT"]
    assert set(stored["df"]["symbol"]) == {"BTCUSDT", "CHZUSDT"}


def test_update_history_filter_removes_existing_history_symbols(monkeypatch, config):
    result, stored = _run_update_with_policy(monkeypatch, config, "filter")
    assert result["history_only_symbols"] == []
    assert set(stored["df"]["symbol"]) == {"BTCUSDT"}


def test_update_history_error_keeps_strict_validation(monkeypatch, config):
    with pytest.raises(ValueError, match="unknown symbols"):
        _run_update_with_policy(monkeypatch, config, "error")

from __future__ import annotations

from pathlib import Path

import pytest

from app.training import training_config as module
from app.training.training_config import DEFAULT_SYMBOLS, TrainingConfig


def test_env_parsers(monkeypatch):
    monkeypatch.setenv("BOOL_VALUE", "yes")
    monkeypatch.setenv("INT_VALUE", "7")
    monkeypatch.setenv("FLOAT_VALUE", "1.25")
    monkeypatch.setenv("INT_LIST_VALUE", "1, 2,3")
    monkeypatch.setenv("LIST_VALUE", "btcusdt, ethusdt")

    assert module._env_bool("BOOL_VALUE", False) is True
    assert module._env_bool("MISSING_BOOL", False) is False
    assert module._env_int("INT_VALUE", 0) == 7
    assert module._env_int("MISSING_INT", 9) == 9
    assert module._env_float("FLOAT_VALUE", 0.0) == 1.25
    assert module._env_float("MISSING_FLOAT", 2.5) == 2.5
    assert module._env_int_list("INT_LIST_VALUE", []) == [1, 2, 3]
    assert module._env_int_list("MISSING_INT_LIST", [4]) == [4]
    assert module._env_list("LIST_VALUE", []) == ["BTCUSDT", "ETHUSDT"]
    assert module._env_list("MISSING_LIST", ["BTCUSDT"]) == ["BTCUSDT"]


def test_default_symbols_cover_existing_history_symbols():
    required = {
        "CHZUSDT",
        "FLOWUSDT",
        "GRTUSDT",
        "ICPUSDT",
        "IMXUSDT",
        "LDOUSDT",
        "MINAUSDT",
        "QNTUSDT",
        "RENDERUSDT",
        "SHIBUSDT",
        "STXUSDT",
        "THETAUSDT",
        "TIAUSDT",
        "TONUSDT",
        "USDCUSDT",
    }
    assert required.issubset(set(DEFAULT_SYMBOLS))


def test_post_init_normalizes_symbols_paths_and_purge(tmp_path):
    config = TrainingConfig(
        app_dir=tmp_path,
        symbols=["btc/usdt", "BTC-USDT", "ethusdt"],
        target_horizon=5,
        purge_bars=1,
    )
    assert config.symbols == ["BTCUSDT", "ETHUSDT"]
    assert config.purge_bars == 5
    assert config.history_path == tmp_path / "training" / "data" / "history_data.parquet"
    assert config.registry_path == tmp_path / "models" / "registry.json"


def test_invalid_config_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="ratios"):
        TrainingConfig(app_dir=tmp_path, train_ratio=0.8)
    with pytest.raises(ValueError, match="target_horizon"):
        TrainingConfig(app_dir=tmp_path, target_horizon=0)
    with pytest.raises(ValueError, match="at least one symbol"):
        TrainingConfig(app_dir=tmp_path, symbols=[])
    with pytest.raises(ValueError, match="history_symbol_policy"):
        TrainingConfig(app_dir=tmp_path, history_symbol_policy="unknown")


def test_from_env_and_to_dict(monkeypatch, tmp_path):
    monkeypatch.setenv("ML_SYMBOLS", "btcusdt,ethusdt")
    monkeypatch.setenv("ML_HISTORY_SYMBOL_POLICY", "filter")
    monkeypatch.setenv("TRAINING_WINDOW_DAYS", "90")
    monkeypatch.setenv("ML_HISTORY_PATH", str(tmp_path / "history.parquet"))
    config = TrainingConfig.from_env()
    assert config.symbols == ["BTCUSDT", "ETHUSDT"]
    assert config.history_symbol_policy == "filter"
    assert config.training_window_days == 90
    assert config.history_path == (tmp_path / "history.parquet").resolve()
    payload = config.to_dict()
    assert isinstance(payload["history_path"], str)


def test_model_search_space_has_named_candidates(config):
    candidates = config.model_search_space
    assert len(candidates) >= 3
    assert all("name" in item and "iterations" in item for item in candidates)

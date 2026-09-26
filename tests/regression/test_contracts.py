from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_outcome_settings_exist_and_validate():
    from app.backend.api.app.config import Settings

    settings = Settings(_env_file=None, OUTCOME_AUTO_EVALUATION=False)
    for name in (
        "OUTCOME_TARGET_HORIZON_BARS",
        "OUTCOME_TARGET_HORIZON_MINUTES",
        "OUTCOME_FEE",
        "OUTCOME_SLIPPAGE",
        "OUTCOME_MIN_NET_RETURN",
        "OUTCOME_MAX_DRAWDOWN",
        "OUTCOME_AUTO_EVALUATION",
        "OUTCOME_CHECK_INTERVAL_SECONDS",
        "OUTCOME_BATCH_SIZE",
        "OUTCOME_MAX_RETRIES",
    ):
        assert hasattr(settings, name)
    with pytest.raises(Exception):
        Settings(_env_file=None, OUTCOME_TARGET_HORIZON_BARS=0)
    with pytest.raises(Exception):
        Settings(_env_file=None, OUTCOME_FEE=-0.1)


def test_dependency_contract_is_identical_and_pinned():
    expected = {
        "grpcio==1.81.1",
        "grpcio-tools==1.81.1",
        "grpcio-health-checking==1.81.1",
        "protobuf==6.33.5",
    }
    backend = set((ROOT / "app/backend/api/requirements.txt").read_text(encoding="utf-8").splitlines())
    ml = set((ROOT / "app/ml_services/requirements.txt").read_text(encoding="utf-8").splitlines())
    assert expected <= backend
    assert expected <= ml


def test_compose_persists_sqlite_and_uses_application_healthchecks():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    backend = compose["services"]["backend"]
    ml = compose["services"]["ml_service"]
    assert "backend_data:/app/data" in backend["volumes"]
    assert "backend_data" in compose["volumes"]
    assert "healthcheck" in backend
    assert ml["healthcheck"]["test"] == ["CMD", "python", "-m", "app.online.healthcheck"]
    assert backend["depends_on"]["ml_service"]["condition"] == "service_healthy"


def test_strategy_selection_prefers_allowed_margin_and_is_deterministic():
    from app.backend.api.app.services.strategy_selection import select_best_prediction

    def pred(p, threshold, allowed):
        return SimpleNamespace(prob_good_trade=p, threshold=threshold, trade_allowed=allowed)

    # Higher raw p is denied, lower p passes its own strategy gate.
    selected, _ = select_best_prediction([
        ("breakout", pred(0.42, 0.40, True)),
        ("mean_reversion", pred(0.50, 0.60, False)),
    ])
    assert selected == "breakout"

    selected, _ = select_best_prediction([
        ("breakout", pred(0.46, 0.40, True)),
        ("mean_reversion", pred(0.63, 0.60, True)),
    ])
    assert selected == "breakout"  # margin .06 vs .03

    selected, _ = select_best_prediction([
        ("breakout", pred(0.35, 0.40, False)),
        ("mean_reversion", pred(0.50, 0.60, False)),
    ])
    assert selected == "breakout"  # denied diagnostics: -.05 beats -.10

    selected, _ = select_best_prediction([
        ("mean_reversion", pred(0.45, 0.40, True)),
        ("breakout", pred(0.45, 0.40, True)),
    ])
    assert selected == "breakout"


def test_strict_inference_never_falls_back_to_previous_row():
    from app.ml_services.app.features_builder import latest_strict_inference_row

    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01T00:00:00", "2026-01-01T01:00:00"]),
            "x": [1.0, float("nan")],
        }
    )
    with pytest.raises(ValueError, match="latest closed candle"):
        latest_strict_inference_row(frame, ["timestamp", "x"])


def test_risk_engine_uses_model_target_contract_over_backend_defaults():
    from app.backend.api.app.services.risk_service import calculate_risk_parameters

    result = calculate_risk_parameters(
        account_balance=1000,
        risk_per_trade_pct=1,
        max_position_share_pct=100,
        entry_price=100,
        atr_14_pct=0.01,
        probability=0.6,
        threshold=0.5,
        model_trade_allowed=True,
        atr_stop_multiplier=2.0,
        min_stop_loss_pct=0.5,
        risk_reward_ratio=3.0,
    )
    assert result["stop_loss_pct"] == pytest.approx(2.0)
    assert result["take_profit_pct"] == pytest.approx(6.0)
    assert result["risk_reward_ratio"] == pytest.approx(3.0)


def test_entry_semantics_do_not_store_signal_close_as_real_entry():
    source = (ROOT / "app/backend/api/app/routers/trade_decision_router.py").read_text(encoding="utf-8")
    assert '"entry_price": None' in source
    assert "signal_close_price" in source
    assert "planned_entry_price" in source
    assert "entry_convention" in source


def test_target_contract_exit_semantics_match_first_touch():
    source = (ROOT / "app/ml_services/app/training/train_model.py").read_text(encoding="utf-8")
    assert "first_touch_tp_sl_then_timeout" in source
    assert '"target_definition": config.target_definition' in source


def test_outcome_snapshot_columns_are_persisted():
    source = (ROOT / "app/backend/api/app/storage/database.py").read_text(encoding="utf-8")
    for column in (
        "target_definition",
        "target_horizon_minutes",
        "target_horizon_bars",
        "target_fee",
        "target_slippage",
        "entry_convention",
        "exit_convention",
        "feature_schema_version",
        "model_version",
    ):
        assert column in source


def test_frontend_exposes_only_model_supported_choices_and_avoids_innerhtml():
    js = (ROOT / "app/backend/api/app/static/app.js").read_text(encoding="utf-8")
    html = (ROOT / "app/backend/api/app/static/index.html").read_text(encoding="utf-8")
    assert "data.supported_intervals" in js
    assert "data.supported_exchanges" in js
    assert "innerHTML" not in js
    assert '<select id="interval"></select>' in html
    assert '<select id="exchange"></select>' in html


def test_schema_migration_requires_explicit_flag_in_pipeline():
    source = (ROOT / "app/ml_services/app/training/retrain_pipeline.py").read_text(encoding="utf-8")
    assert "--allow-schema-migration" in source
    assert "schema_upgrade" in source
    assert "schema_migration_authorized" in source


def test_proto_source_contains_single_current_contract():
    text = (ROOT / "app/proto/ml/v1/ml.proto").read_text(encoding="utf-8")
    assert text.count("service MLService") == 1
    for field in (
        "string symbol = 1;",
        "string interval = 2;",
        "string strategy_name = 3;",
        "repeated Candle candles = 4;",
        "double raw_prob_good_trade = 7;",
        "string calibration_method = 8;",
    ):
        assert field in text


def test_env_example_integrates_outcome_settings():
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    for name in (
        "OUTCOME_TARGET_HORIZON_BARS",
        "OUTCOME_FEE",
        "OUTCOME_SLIPPAGE",
        "OUTCOME_AUTO_EVALUATION",
        "OUTCOME_CHECK_INTERVAL_SECONDS",
        "OUTCOME_BATCH_SIZE",
    ):
        assert f"{name}=" in env
    assert not (ROOT / ".env.example.outcome-additions").exists()

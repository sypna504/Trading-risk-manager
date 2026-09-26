from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from ..config import settings


def _safe_relative_path(value: str | Path) -> Path:
    normalized = str(value).strip().replace("\\", "/")
    if not normalized:
        raise ValueError("registry artifact path is empty")
    pure = PurePosixPath(normalized)
    parts = tuple(part for part in pure.parts if part not in ("", "."))
    if pure.is_absolute() or not parts or ".." in parts or ":" in parts[0]:
        raise ValueError(f"unsafe registry artifact path: {value}")
    return Path(*parts)


def _resolve_inside_root(root: Path, value: str | Path) -> Path:
    resolved_root = root.resolve()
    resolved = (resolved_root / _safe_relative_path(value)).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"registry artifact is outside models root: {value}") from error
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _parse_utc(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_model_artifacts() -> tuple[Path, Path, str | None]:
    models_root = Path(settings.MODELS_ROOT)
    registry_path = Path(settings.MODEL_REGISTRY_PATH)
    if registry_path.exists():
        registry = _read_json(registry_path)
        version = registry.get("active_model_version")
        model_value = registry.get("active_model_path")
        config_value = registry.get("active_config_path")
        if version and model_value and config_value:
            return (
                _resolve_inside_root(models_root, model_value),
                _resolve_inside_root(models_root, config_value),
                str(version),
            )
    return Path(settings.MODEL_PATH), Path(settings.MODEL_CONFIG_PATH), None


def _normalize_config(
    config: dict[str, Any],
    *,
    config_path: Path,
    registry_version: str | None,
) -> tuple[dict[str, Any], list[str]]:
    result = dict(config)
    warnings: list[str] = []
    bundle_dir = config_path.parent
    dataset_report = _read_json(bundle_dir / "dataset_report.json")
    training_report = _read_json(bundle_dir / "training_report.json")

    schema = str(result.get("feature_schema_version") or "legacy_v2")
    result["feature_schema_version"] = schema
    result.setdefault("model_version", registry_version or "unknown")
    result.setdefault("supported_intervals", ["1h"])
    result.setdefault("supported_strategies", ["breakout", "mean_reversion"])
    result.setdefault("target_horizon_minutes", 180)
    result.setdefault("target_horizon_bars", 3)
    result.setdefault(
        "target_definition",
        "horizon_return_drawdown" if schema == "legacy_v2" else "first_touch_atr_rr",
    )
    result.setdefault("minimum_net_return", 0.002)
    result.setdefault("maximum_target_drawdown", -0.015)
    result.setdefault("fee", 0.001)
    result.setdefault("slippage", 0.0005)
    result.setdefault("risk_atr_stop_multiplier", 1.5)
    result.setdefault("risk_min_stop_loss_pct", 0.5)
    result.setdefault("risk_reward_ratio", 2.0)
    result.setdefault("intrabar_priority", "stop_loss")
    result.setdefault("entry_convention", "next_bar_open")
    result.setdefault(
        "exit_convention",
        "first_touch_tp_sl_then_timeout"
        if result["target_definition"] == "first_touch_atr_rr"
        else "horizon_bar_close",
    )

    supported_symbols = list(result.get("supported_symbols") or [])
    if not supported_symbols:
        supported_symbols = list(dataset_report.get("symbols") or [])
    if not supported_symbols and training_report:
        for metrics_key in ("test_metrics", "raw_test_metrics"):
            by_symbol = (
                training_report.get(metrics_key, {})
                .get("trading", {})
                .get("by_symbol", {})
            )
            if by_symbol:
                supported_symbols = sorted(str(value).upper() for value in by_symbol)
                break
    result["supported_symbols"] = list(dict.fromkeys(supported_symbols))
    result.setdefault("allow_unseen_symbols", False)
    if not result["supported_symbols"]:
        warnings.append(
            "training symbol universe is unavailable; trade-ready compatibility cannot be proven"
        )

    exchanges = list(result.get("supported_exchanges") or [])
    if not exchanges:
        exchange = dataset_report.get("exchange")
        if exchange:
            exchanges = [str(exchange).lower()]
        elif result.get("exchange"):
            exchanges = [str(result["exchange"]).lower()]
        else:
            # Historical bundles in this project were trained on Binance.
            exchanges = ["binance"] if schema == "legacy_v2" else []
            if not exchanges:
                warnings.append("training exchange is unavailable")
    result["supported_exchanges"] = exchanges

    result.setdefault("evaluation_train_end", result.get("train_end"))
    result.setdefault("evaluation_test_end", result.get("test_end"))
    result.setdefault("production_train_end", result.get("train_end"))
    result.setdefault("calibration_method", "none")

    explicit_status = result.get("model_status")
    if explicit_status:
        model_status = str(explicit_status)
    elif schema == "legacy_v2":
        model_status = "legacy_experimental"
    else:
        # Active v3 bundles must still expose validation provenance. A bundle
        # without it is experimental rather than silently considered validated.
        promotion = _read_json(bundle_dir / "promotion_decision.json")
        if promotion.get("passed") is True:
            model_status = "validated"
        else:
            model_status = "experimental"
    result["model_status"] = model_status

    # Preserve validation provenance if it exists in the training report.
    if training_report:
        result.setdefault(
            "evaluation_test_end",
            training_report.get("split", {}).get("test_end")
            or training_report.get("test_end"),
        )

    return result, warnings


def read_active_model_metadata() -> dict[str, Any]:
    model_path, config_path, registry_version = resolve_model_artifacts()
    if not config_path.exists():
        return {
            "model_path": model_path,
            "config_path": config_path,
            "model_file_exists": model_path.exists(),
            "config_file_exists": False,
            "model_version": registry_version,
            "config": {},
            "compatibility_warnings": ["active model config is missing"],
            "data_age_hours": None,
            "is_model_stale": None,
        }

    raw_config = _read_json(config_path)
    config, warnings = _normalize_config(
        raw_config,
        config_path=config_path,
        registry_version=registry_version,
    )
    production_train_end = _parse_utc(config.get("production_train_end"))
    data_age_hours: float | None = None
    is_model_stale: bool | None = None
    if production_train_end is not None:
        data_age_hours = max(
            0.0,
            (datetime.now(timezone.utc) - production_train_end).total_seconds() / 3600,
        )
        is_model_stale = data_age_hours > settings.MODEL_MAX_AGE_DAYS * 24
        if is_model_stale:
            warnings.append(
                f"model production data is stale: {data_age_hours:.1f} hours old"
            )

    return {
        "model_path": model_path,
        "config_path": config_path,
        "model_file_exists": model_path.exists(),
        "config_file_exists": True,
        "model_version": config.get("model_version") or registry_version,
        "config": config,
        "compatibility_warnings": warnings,
        "data_age_hours": data_age_hours,
        "is_model_stale": is_model_stale,
    }

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import settings
from .model_metadata_service import read_active_model_metadata


class ModelCompatibilityError(RuntimeError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class CompatibilityResult:
    metadata: dict[str, Any]
    config: dict[str, Any]
    warnings: tuple[str, ...]

    @property
    def model_version(self) -> str:
        return str(self.metadata.get("model_version") or "unknown")

    @property
    def model_status(self) -> str:
        return str(self.config.get("model_status") or "experimental")


def check_model_compatibility(
    *,
    exchange: str,
    symbol: str,
    interval: str,
    strategy: str | None = None,
    require_trade_ready: bool = False,
) -> CompatibilityResult:
    metadata = read_active_model_metadata()
    if not metadata.get("model_file_exists") or not metadata.get("config_file_exists"):
        raise ModelCompatibilityError(
            "active model artifacts are unavailable",
            status_code=503,
        )

    config = dict(metadata.get("config") or {})
    version = str(metadata.get("model_version") or "unknown")
    normalized_exchange = exchange.strip().lower()
    normalized_symbol = symbol.strip().upper().replace("/", "").replace("-", "")
    normalized_interval = interval.strip()

    supported_intervals = list(config.get("supported_intervals") or [])
    if normalized_interval not in supported_intervals:
        raise ModelCompatibilityError(
            f"active model {version} does not support interval {normalized_interval}; "
            f"supported intervals: {supported_intervals}",
            status_code=400,
        )

    supported_exchanges = [
        str(value).lower() for value in (config.get("supported_exchanges") or [])
    ]
    if supported_exchanges and normalized_exchange not in supported_exchanges:
        raise ModelCompatibilityError(
            f"active model {version} was not validated for exchange {normalized_exchange}; "
            f"supported exchanges: {supported_exchanges}",
            status_code=400,
        )

    supported_strategies = list(config.get("supported_strategies") or [])
    if strategy is not None and strategy not in supported_strategies:
        raise ModelCompatibilityError(
            f"active model {version} does not support strategy {strategy}; "
            f"supported strategies: {supported_strategies}",
            status_code=400,
        )

    supported_symbols = [
        str(value).upper().replace("/", "").replace("-", "")
        for value in (config.get("supported_symbols") or [])
    ]
    allow_unseen = bool(config.get("allow_unseen_symbols", False))
    if not allow_unseen:
        if supported_symbols and normalized_symbol not in supported_symbols:
            raise ModelCompatibilityError(
                f"symbol {normalized_symbol} is outside the training universe of model {version}",
                status_code=400,
            )
        if require_trade_ready and not supported_symbols:
            raise ModelCompatibilityError(
                f"model {version} does not declare its training symbol universe",
                status_code=503,
            )

    status = str(config.get("model_status") or "experimental")
    if status == "rejected":
        raise ModelCompatibilityError(
            f"active model {version} is marked rejected",
            status_code=503,
        )
    if require_trade_ready and settings.MODEL_REQUIRE_VALIDATED_STATUS:
        if status != "validated":
            raise ModelCompatibilityError(
                f"active model {version} status is {status}, not validated",
                status_code=503,
            )

    stale = metadata.get("is_model_stale")
    if require_trade_ready and stale and settings.MODEL_BLOCK_TRADES_WHEN_STALE:
        raise ModelCompatibilityError(
            f"active model {version} is stale and trade recommendations are blocked",
            status_code=503,
        )

    warnings = list(metadata.get("compatibility_warnings") or [])
    if status == "legacy_experimental":
        warnings.append("active model is a legacy experimental fallback")
    return CompatibilityResult(
        metadata=metadata,
        config=config,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def target_contract_snapshot(result: CompatibilityResult) -> dict[str, Any]:
    config = result.config
    interval = list(config.get("supported_intervals") or ["1h"])[0]
    horizon_minutes = int(config.get("target_horizon_minutes") or 180)
    horizon_bars = int(config.get("target_horizon_bars") or 0)
    if horizon_bars <= 0:
        if interval == "1h" and horizon_minutes % 60 == 0:
            horizon_bars = horizon_minutes // 60
        else:
            horizon_bars = settings.OUTCOME_TARGET_HORIZON_BARS
    return {
        "target_definition": str(config.get("target_definition") or "horizon_return_drawdown"),
        "target_horizon_minutes": horizon_minutes,
        "target_horizon_bars": horizon_bars,
        "target_min_net_return": float(
            config.get("minimum_net_return", settings.OUTCOME_MIN_NET_RETURN)
        ),
        "target_max_drawdown": float(
            config.get("maximum_target_drawdown", settings.OUTCOME_MAX_DRAWDOWN)
        ),
        "target_fee": float(config.get("fee", settings.OUTCOME_FEE)),
        "target_slippage": float(config.get("slippage", settings.OUTCOME_SLIPPAGE)),
        "risk_atr_stop_multiplier": float(config.get("risk_atr_stop_multiplier", 1.5)),
        "risk_min_stop_loss_pct": float(config.get("risk_min_stop_loss_pct", 0.5)),
        "risk_reward_ratio": float(config.get("risk_reward_ratio", 2.0)),
        "intrabar_priority": str(config.get("intrabar_priority") or "stop_loss"),
        "entry_convention": str(config.get("entry_convention") or "next_bar_open"),
        "exit_convention": str(config.get("exit_convention") or "horizon_bar_close"),
        "model_version": result.model_version,
        "feature_schema_version": str(
            config.get("feature_schema_version") or "legacy_v2"
        ),
        "model_status": result.model_status,
        "calibration_method": str(config.get("calibration_method") or "none"),
    }

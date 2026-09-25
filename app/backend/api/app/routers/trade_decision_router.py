from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.news_intelligence.service import NewsIntelligenceService
from app.news_intelligence.storage import NewsRepository

from ..config import settings
from ..grpc_client import (
    MLGrpcClient,
    MLModelUnavailableError,
    MLUpstreamError,
)
from ..schemas.trade_decision_schemas import (
    OutcomeEvaluationResponse,
    OutcomeSummaryResponse,
    StoredDecisionResponse,
    TradeDecisionResponse,
)
from ..services.market_services import GetCandles
from ..services.model_compatibility import (
    CompatibilityResult,
    ModelCompatibilityError,
    check_model_compatibility,
    target_contract_snapshot,
)
from ..services.outcome_service import OutcomeEvaluator, outcome_due_at
from ..services.risk_service import calculate_risk_parameters
from ..services.signal_service import detect_trading_signal
from ..services.strategy_selection import prediction_margin, select_best_prediction
from ..storage.decision_repository import DecisionRepository


logger = logging.getLogger(__name__)
trade_router = APIRouter(prefix="/trading")
trade_ml_client = MLGrpcClient()
repository = DecisionRepository()
outcome_evaluator = OutcomeEvaluator(repository)
# Backward-compatible private alias used by older audit callers.
_select_best_prediction = select_best_prediction


NEWS_INFORMATIONAL_DISCLAIMER = (
    "news layer is informational and does not alter the ML trading gate"
)


def _download_candles(
    exchange: str,
    symbol: str,
    interval: str,
    limit: int,
):
    downloader = GetCandles(symbol=symbol, interval=interval, limit=limit)
    return (
        downloader.get_bybit_candles_dc().items
        if exchange == "bybit"
        else downloader.get_binance_candles().items
    )


def _validate_prediction(strategy_name: str, prediction) -> None:
    numeric_fields = {
        "prob_good_trade": prediction.prob_good_trade,
        "raw_prob_good_trade": getattr(
            prediction, "raw_prob_good_trade", prediction.prob_good_trade
        ),
        "risk_score": prediction.risk_score,
        "threshold": prediction.threshold,
    }
    for field_name, value in numeric_fields.items():
        numeric_value = float(value)
        if not math.isfinite(numeric_value) or not 0 <= numeric_value <= 1:
            raise MLUpstreamError(
                f"ML service returned invalid {field_name} for "
                f"{strategy_name}: {value}"
            )
    if not str(prediction.model_version).strip():
        raise MLUpstreamError(
            f"ML service returned an empty model_version for {strategy_name}"
        )


def _get_strategy_predictions(
    *,
    active_strategies: list[str],
    symbol: str,
    interval: str,
    candles,
):
    predictions = []
    failures: dict[str, str] = {}
    for strategy_name in active_strategies:
        try:
            prediction = trade_ml_client.predict_quality(
                symbol=symbol,
                interval=interval,
                strategy_name=strategy_name,
                candles=candles,
            )
            _validate_prediction(strategy_name, prediction)
            predictions.append((strategy_name, prediction))
        except (MLUpstreamError, MLModelUnavailableError, ConnectionError, ValueError) as error:
            failures[strategy_name] = str(error)
    if not predictions:
        details = "; ".join(
            f"{strategy}: {message}" for strategy, message in failures.items()
        )
        raise MLUpstreamError(
            "ML service could not evaluate any active strategy"
            + (f": {details}" if details else "")
        )
    model_versions = {
        str(prediction.model_version) for _, prediction in predictions
    }
    if len(model_versions) != 1:
        raise MLUpstreamError(
            "active model changed during multi-strategy evaluation; retry the request"
        )
    return predictions, failures


def _load_news_context(symbol: str, decision_time: datetime) -> dict | None:
    """Best-effort news context. Failures never fail the trading decision."""
    if not settings.NEWS_CONTEXT_ENABLED:
        return None
    try:
        news_repository = NewsRepository(settings.DATABASE_PATH)
        news_service = NewsIntelligenceService(news_repository)
        return news_service.get_market_news_context(symbol, decision_time)
    except Exception as error:
        logger.warning("news context unavailable for %s: %s", symbol, error)
        return None


def _news_reason(base_reason: str, news_context: dict | None) -> str:
    if news_context is None:
        return base_reason

    count = int(news_context.get("news_count", 0))
    if count == 0:
        summary = "no recent relevant news"
    else:
        regulatory = float(news_context.get("regulatory_risk_score", 0.0))
        geopolitical = float(news_context.get("geopolitical_risk_score", 0.0))
        macro = float(news_context.get("macro_risk_score", 0.0))
        risk_level = str(news_context.get("risk_level", "low"))
        category = max(
            ((regulatory, "regulatory"), (geopolitical, "geopolitical"), (macro, "macro")),
            key=lambda pair: pair[0],
        )
        if risk_level == "high" and category[0] > 0:
            summary = f"high {category[1]} activity"
        else:
            summary = f"{risk_level} risk across {count} relevant event(s)"

    return f"{base_reason}; news context: {summary}; {NEWS_INFORMATIONAL_DISCLAIMER}"


def _store_decision(
    *,
    checked_at: str,
    exchange: str,
    symbol: str,
    interval: str,
    candles_count: int,
    signal_result: dict,
    selected_strategy: str | None,
    prediction,
    risk_parameters: dict | None,
    account_balance: float,
    risk_per_trade_pct: float,
    status: str,
    reason: str,
    compatibility: CompatibilityResult,
    news_context: dict | None = None,
) -> int:
    signal_timestamp = signal_result.get("timestamp")
    target = target_contract_snapshot(compatibility)
    outcome_status = (
        "pending" if signal_result["signal_detected"] else "not_applicable"
    )
    due_at = (
        outcome_due_at(
            signal_timestamp,
            interval,
            int(target["target_horizon_bars"]),
        )
        if signal_result["signal_detected"] and signal_timestamp
        else None
    )
    signal_close = signal_result.get("close")
    planned_entry = signal_close if signal_result["signal_detected"] else None
    return repository.save(
        {
            "created_at": checked_at,
            "exchange": exchange,
            "symbol": symbol.upper(),
            "interval": interval,
            "candles_count": candles_count,
            "signal_detected": signal_result["signal_detected"],
            "active_strategies": signal_result["active_strategies"],
            "selected_strategy": selected_strategy,
            "probability": (
                float(prediction.prob_good_trade) if prediction else None
            ),
            "raw_probability": (
                float(getattr(prediction, "raw_prob_good_trade", prediction.prob_good_trade)) if prediction else None
            ),
            "threshold": float(prediction.threshold) if prediction else None,
            "risk_score": float(prediction.risk_score) if prediction else None,
            "risk_level": prediction.risk_level if prediction else None,
            "trade_allowed": (
                bool(prediction.trade_allowed) if prediction else False
            ),
            "model_version": target["model_version"],
            "feature_schema_version": target["feature_schema_version"],
            "model_status": target["model_status"],
            "calibration_method": (
                getattr(prediction, "calibration_method", target["calibration_method"])
                if prediction
                else target["calibration_method"]
            ),
            "market_regime": signal_result.get("market_regime"),
            # Compatibility alias only; not a fill price.
            "entry_price": None,
            "signal_close_price": signal_close,
            "planned_entry_price": planned_entry,
            "entry_convention": target["entry_convention"],
            "exit_convention": target["exit_convention"],
            "stop_loss_price": (
                risk_parameters.get("stop_loss_price") if risk_parameters else None
            ),
            "take_profit_price": (
                risk_parameters.get("take_profit_price") if risk_parameters else None
            ),
            "position_size": (
                risk_parameters.get("recommended_position_size")
                if risk_parameters
                else 0.0
            ),
            "position_notional": (
                risk_parameters.get("recommended_position_notional")
                if risk_parameters
                else 0.0
            ),
            "account_balance": account_balance,
            "risk_per_trade_pct": risk_per_trade_pct,
            "status": status,
            "reason": reason,
            "news_context_available": news_context is not None,
            "news_risk_level": (
                str(news_context.get("risk_level")) if news_context is not None else None
            ),
            "news_count": (
                int(news_context.get("news_count", 0)) if news_context is not None else 0
            ),
            "high_impact_news_count": (
                int(news_context.get("high_impact_count", 0))
                if news_context is not None
                else 0
            ),
            "signal_timestamp": signal_timestamp,
            "outcome_due_at": due_at,
            "outcome_status": outcome_status,
            **{
                key: target[key]
                for key in (
                    "target_definition",
                    "target_horizon_minutes",
                    "target_horizon_bars",
                    "target_min_net_return",
                    "target_max_drawdown",
                    "target_fee",
                    "target_slippage",
                )
            },
            "target_stop_loss_fraction": (
                float(risk_parameters.get("stop_loss_pct")) / 100.0
                if risk_parameters
                else None
            ),
            "target_risk_reward_ratio": float(target.get("risk_reward_ratio", 2.0)),
            "target_intrabar_priority": str(target.get("intrabar_priority", "stop_loss")),
        }
    )


def _compatibility_or_http(**kwargs) -> CompatibilityResult:
    try:
        return check_model_compatibility(**kwargs)
    except ModelCompatibilityError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@trade_router.get("/decision", response_model=TradeDecisionResponse)
def get_trade_decision(
    exchange: Literal["binance", "bybit"] = "binance",
    symbol: str = Query(default="BTCUSDT", min_length=3),
    interval: str = Query(default="1h", min_length=2, max_length=8),
    limit: int = Query(default=500, ge=60, le=5000),
    account_balance: float = Query(default=1000.0, gt=0),
    risk_per_trade_pct: float = Query(default=1.0, gt=0, le=10),
    max_position_share_pct: float = Query(default=25.0, ge=1, le=100),
):
    decision_time = datetime.now(timezone.utc)
    checked_at = decision_time.isoformat()
    compatibility = _compatibility_or_http(
        exchange=exchange,
        symbol=symbol,
        interval=interval,
        require_trade_ready=True,
    )
    try:
        candles = _download_candles(exchange, symbol, interval, limit)
        signal_result = detect_trading_signal(candles, symbol, interval)
        target = target_contract_snapshot(compatibility)
        warnings = list(compatibility.warnings)

        if not signal_result["signal_detected"]:
            news_context = _load_news_context(symbol, decision_time)
            reason = _news_reason(signal_result["reason"], news_context)
            decision_id = _store_decision(
                checked_at=checked_at,
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                candles_count=len(candles),
                signal_result=signal_result,
                selected_strategy=None,
                prediction=None,
                risk_parameters=None,
                account_balance=account_balance,
                risk_per_trade_pct=risk_per_trade_pct,
                status="no_signal",
                reason=reason,
                compatibility=compatibility,
                news_context=news_context,
            )
            return TradeDecisionResponse(
                id=decision_id,
                status="no_signal",
                signal_detected=False,
                trade_allowed=False,
                active_strategies=[],
                selected_strategy=None,
                strategy_name=None,
                reason=reason,
                exchange=exchange,
                symbol=symbol.upper(),
                interval=interval,
                candles_count=len(candles),
                checked_at=checked_at,
                entry_price=None,
                signal_close_price=signal_result["close"],
                planned_entry_price=None,
                entry_convention=target["entry_convention"],
                model_version=target["model_version"],
                feature_schema_version=target["feature_schema_version"],
                model_status=target["model_status"],
                calibration_method=target["calibration_method"],
                model_warnings=warnings,
                news_context=news_context,
                signal_timestamp=signal_result.get("timestamp"),
                outcome_status="not_applicable",
            )

        # Use the same compatibility checker for each model-bound strategy.
        for strategy_name in signal_result["active_strategies"]:
            _compatibility_or_http(
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                strategy=strategy_name,
                require_trade_ready=True,
            )

        predictions, prediction_failures = _get_strategy_predictions(
            active_strategies=signal_result["active_strategies"],
            symbol=symbol,
            interval=interval,
            candles=candles,
        )
        selected_strategy, best_prediction = select_best_prediction(predictions)

        # The true target entry is next_bar_open and is not known yet. The risk
        # engine uses signal close only as a planning estimate.
        planned_entry_price = float(signal_result["close"])
        risk_parameters = calculate_risk_parameters(
            account_balance=account_balance,
            risk_per_trade_pct=risk_per_trade_pct,
            max_position_share_pct=max_position_share_pct,
            entry_price=planned_entry_price,
            atr_14_pct=signal_result["atr_14_pct"],
            probability=best_prediction.prob_good_trade,
            threshold=best_prediction.threshold,
            model_trade_allowed=best_prediction.trade_allowed,
            signal_detected=True,
            atr_stop_multiplier=float(target["risk_atr_stop_multiplier"]),
            min_stop_loss_pct=float(target["risk_min_stop_loss_pct"]),
            risk_reward_ratio=float(target["risk_reward_ratio"]),
        )

        reason = (
            f"{signal_result['reason']}; selected {selected_strategy} by "
            "trade_allowed first, then probability-threshold margin"
        )
        if target["entry_convention"] == "next_bar_open":
            reason += "; risk levels use signal close as an estimate of next-bar-open entry"
        if prediction_failures:
            reason += "; unavailable strategies: " + ", ".join(
                sorted(prediction_failures)
            )

        # News is intentionally loaded only after the ML prediction and risk
        # calculation. It cannot influence strategy selection, probability,
        # threshold, trade_allowed, stop loss or position sizing.
        news_context = _load_news_context(symbol, decision_time)
        reason = _news_reason(reason, news_context)

        decision_id = _store_decision(
            checked_at=checked_at,
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            candles_count=len(candles),
            signal_result=signal_result,
            selected_strategy=selected_strategy,
            prediction=best_prediction,
            risk_parameters=risk_parameters,
            account_balance=account_balance,
            risk_per_trade_pct=risk_per_trade_pct,
            status="evaluated",
            reason=reason,
            compatibility=compatibility,
            news_context=news_context,
        )
        due_at = outcome_due_at(
            signal_result["timestamp"],
            interval,
            int(target["target_horizon_bars"]),
        )
        logger.info(
            "symbol=%s interval=%s strategy=%s p=%.6f threshold=%.6f "
            "margin=%.6f allowed=%s model=%s status=%s",
            symbol,
            interval,
            selected_strategy,
            float(best_prediction.prob_good_trade),
            float(best_prediction.threshold),
            prediction_margin(best_prediction),
            bool(best_prediction.trade_allowed),
            best_prediction.model_version,
            target["model_status"],
        )
        return TradeDecisionResponse(
            id=decision_id,
            status="evaluated",
            signal_detected=True,
            trade_allowed=best_prediction.trade_allowed,
            active_strategies=signal_result["active_strategies"],
            selected_strategy=selected_strategy,
            strategy_name=selected_strategy,
            reason=reason,
            exchange=exchange,
            symbol=symbol.upper(),
            interval=interval,
            candles_count=len(candles),
            checked_at=checked_at,
            entry_price=None,
            signal_close_price=signal_result["close"],
            planned_entry_price=planned_entry_price,
            entry_convention=target["entry_convention"],
            prob_good_trade=best_prediction.prob_good_trade,
            raw_prob_good_trade=getattr(best_prediction, "raw_prob_good_trade", best_prediction.prob_good_trade),
            risk_score=best_prediction.risk_score,
            threshold=best_prediction.threshold,
            risk_level=best_prediction.risk_level,
            model_version=best_prediction.model_version,
            feature_schema_version=target["feature_schema_version"],
            model_status=target["model_status"],
            calibration_method=getattr(best_prediction, "calibration_method", target["calibration_method"]),
            model_warnings=warnings,
            risk_parameters=risk_parameters,
            news_context=news_context,
            signal_timestamp=signal_result["timestamp"],
            outcome_due_at=due_at,
            outcome_status="pending",
        )
    except HTTPException:
        raise
    except MLModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except MLUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ConnectionError as error:
        # Exchange request failures are upstream failures.
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("trade decision failed")
        raise HTTPException(status_code=500, detail=str(error)) from error


@trade_router.get("/decisions", response_model=list[StoredDecisionResponse])
def get_decisions(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    symbol: str | None = None,
    strategy: Literal["breakout", "mean_reversion"] | None = None,
    trade_allowed: bool | None = None,
    outcome_status: Literal[
        "pending", "retry", "completed", "invalid_data", "not_applicable"
    ] | None = None,
):
    return repository.list(
        limit=limit,
        offset=offset,
        symbol=symbol,
        strategy=strategy,
        trade_allowed=trade_allowed,
        outcome_status=outcome_status,
    )


@trade_router.post("/outcomes/evaluate", response_model=OutcomeEvaluationResponse)
def evaluate_due_outcomes(
    limit: int = Query(default=100, ge=1, le=500),
):
    return outcome_evaluator.run_once(limit=limit)


@trade_router.get("/outcomes/summary", response_model=OutcomeSummaryResponse)
def get_outcome_summary():
    return repository.outcome_summary()


@trade_router.get("/decisions/{decision_id}", response_model=StoredDecisionResponse)
def get_decision(decision_id: int):
    decision = repository.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return decision

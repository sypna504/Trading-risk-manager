from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..grpc_client import MLGrpcClient
from ..schemas.trade_decision_schemas import (
    StoredDecisionResponse,
    TradeDecisionResponse,
)
from ..services.market_services import GetCandles
from ..services.risk_service import calculate_risk_parameters
from ..services.signal_service import detect_trading_signal
from ..storage.decision_repository import DecisionRepository


logger = logging.getLogger(__name__)
trade_router = APIRouter(prefix="/trading")
trade_ml_client = MLGrpcClient()
repository = DecisionRepository()


def _download_candles(
    exchange: str,
    symbol: str,
    interval: str,
    limit: int,
):
    downloader = GetCandles(
        symbol=symbol,
        interval=interval,
        limit=limit,
    )
    return (
        downloader.get_bybit_candles_dc().items
        if exchange == "bybit"
        else downloader.get_binance_candles().items
    )


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
) -> int:
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
            "threshold": float(prediction.threshold) if prediction else None,
            "risk_score": float(prediction.risk_score) if prediction else None,
            "risk_level": prediction.risk_level if prediction else None,
            "trade_allowed": (
                bool(prediction.trade_allowed) if prediction else False
            ),
            "model_version": prediction.model_version if prediction else None,
            "entry_price": signal_result.get("close"),
            "stop_loss_price": (
                risk_parameters.get("stop_loss_price")
                if risk_parameters
                else None
            ),
            "take_profit_price": (
                risk_parameters.get("take_profit_price")
                if risk_parameters
                else None
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
        }
    )


@trade_router.get("/decision", response_model=TradeDecisionResponse)
def get_trade_decision(
    exchange: Literal["binance", "bybit"] = "binance",
    symbol: str = Query(default="BTCUSDT", min_length=3),
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = "1h",
    limit: int = Query(default=100, ge=60, le=5000),
    account_balance: float = Query(default=1000.0, gt=0),
    risk_per_trade_pct: float = Query(default=1.0, gt=0, le=10),
    max_position_share_pct: float = Query(default=25.0, ge=1, le=100),
):
    checked_at = datetime.now(timezone.utc).isoformat()

    try:
        candles = _download_candles(
            exchange,
            symbol,
            interval,
            limit,
        )
        signal_result = detect_trading_signal(candles, symbol)

        if not signal_result["signal_detected"]:
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
                reason=signal_result["reason"],
            )

            return TradeDecisionResponse(
                id=decision_id,
                status="no_signal",
                signal_detected=False,
                trade_allowed=False,
                active_strategies=[],
                selected_strategy=None,
                strategy_name=None,
                reason=signal_result["reason"],
                exchange=exchange,
                symbol=symbol.upper(),
                interval=interval,
                candles_count=len(candles),
                checked_at=checked_at,
                entry_price=signal_result["close"],
            )

        predictions = []
        for strategy_name in signal_result["active_strategies"]:
            prediction = trade_ml_client.predict_quality(
                symbol=symbol,
                interval=interval,
                strategy_name=strategy_name,
                candles=candles,
            )
            predictions.append((strategy_name, prediction))

        selected_strategy, best_prediction = max(
            predictions,
            key=lambda item: item[1].prob_good_trade,
        )

        risk_parameters = calculate_risk_parameters(
            account_balance=account_balance,
            risk_per_trade_pct=risk_per_trade_pct,
            max_position_share_pct=max_position_share_pct,
            entry_price=signal_result["close"],
            atr_14_pct=signal_result["atr_14_pct"],
            probability=best_prediction.prob_good_trade,
            threshold=best_prediction.threshold,
            model_trade_allowed=best_prediction.trade_allowed,
            signal_detected=True,
        )

        reason = (
            f"{signal_result['reason']}; selected {selected_strategy} "
            "by highest model probability"
        )
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
        )

        logger.info(
            "exchange=%s symbol=%s interval=%s strategy=%s "
            "model_version=%s trade_allowed=%s",
            exchange,
            symbol,
            interval,
            selected_strategy,
            best_prediction.model_version,
            best_prediction.trade_allowed,
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
            entry_price=signal_result["close"],
            prob_good_trade=best_prediction.prob_good_trade,
            risk_score=best_prediction.risk_score,
            threshold=best_prediction.threshold,
            risk_level=best_prediction.risk_level,
            model_version=best_prediction.model_version,
            risk_parameters=risk_parameters,
        )
    except HTTPException:
        raise
    except ConnectionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("trade decision failed")
        raise HTTPException(status_code=500, detail=str(error)) from error


@trade_router.get(
    "/decisions",
    response_model=list[StoredDecisionResponse],
)
def get_decisions(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    symbol: str | None = None,
    strategy: Literal["breakout", "mean_reversion"] | None = None,
    trade_allowed: bool | None = None,
):
    return repository.list(
        limit=limit,
        offset=offset,
        symbol=symbol,
        strategy=strategy,
        trade_allowed=trade_allowed,
    )


@trade_router.get(
    "/decisions/{decision_id}",
    response_model=StoredDecisionResponse,
)
def get_decision(decision_id: int):
    decision = repository.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return decision

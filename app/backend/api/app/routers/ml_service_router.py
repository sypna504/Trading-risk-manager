from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..grpc_client import (
    MLGrpcClient,
    MLModelUnavailableError,
    MLUpstreamError,
)
from ..schemas.ml_schemas import MLpredictresponse, ModelInfoResponse
from ..services.market_services import GetCandles
from ..services.model_compatibility import (
    ModelCompatibilityError,
    check_model_compatibility,
)
from ..services.model_metadata_service import read_active_model_metadata


ml_router = APIRouter(prefix="/ml")
ml_client = MLGrpcClient()


def _compatibility_or_http(**kwargs):
    try:
        return check_model_compatibility(**kwargs)
    except ModelCompatibilityError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@ml_router.get("/prediction-quality", response_model=MLpredictresponse)
def prediction_quality(
    exchange: Literal["binance", "bybit"] = "binance",
    symbol: str = Query(default="BTCUSDT", min_length=3),
    interval: str = Query(default="1h", min_length=2, max_length=8),
    strategy_name: Literal["breakout", "mean_reversion"] = "mean_reversion",
    limit: int = Query(default=500, ge=60, le=5000),
):
    compatibility = _compatibility_or_http(
        exchange=exchange,
        symbol=symbol,
        interval=interval,
        strategy=strategy_name,
        require_trade_ready=False,
    )
    try:
        downloader = GetCandles(symbol=symbol, interval=interval, limit=limit)
        candles = (
            downloader.get_bybit_candles_dc().items
            if exchange == "bybit"
            else downloader.get_binance_candles().items
        )
        if len(candles) < settings.MIN_CANDLES:
            raise HTTPException(
                status_code=502,
                detail=f"got: {len(candles)}, required: {settings.MIN_CANDLES}",
            )
        response = ml_client.predict_quality(
            symbol=symbol,
            interval=interval,
            strategy_name=strategy_name,
            candles=candles,
        )
        return MLpredictresponse(
            exchange=exchange,
            symbol=symbol.upper(),
            interval=interval,
            strategy_name=strategy_name,
            candles_count=len(candles),
            prob_good_trade=response.prob_good_trade,
            raw_prob_good_trade=getattr(response, "raw_prob_good_trade", response.prob_good_trade),
            risk_score=response.risk_score,
            trade_allowed=response.trade_allowed,
            threshold=response.threshold,
            risk_level=response.risk_level,
            model_version=response.model_version,
            feature_schema_version=str(
                compatibility.config.get("feature_schema_version") or "legacy_v2"
            ),
            model_status=compatibility.model_status,
            calibration_method=getattr(response, "calibration_method", str(compatibility.config.get("calibration_method") or "none")),
            probability_bin=getattr(response, "probability_bin", f"{int(float(response.prob_good_trade) * 10) * 10:02d}-{min(100, int(float(response.prob_good_trade) * 10) * 10 + 10):02d}%"),
            model_supported_interval=getattr(response, "model_supported_interval", interval),
            model_warnings=list(compatibility.warnings),
        )
    except HTTPException:
        raise
    except MLModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except MLUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ConnectionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@ml_router.get("/model-info", response_model=ModelInfoResponse)
def get_model_info():
    try:
        metadata = read_active_model_metadata()
        config = metadata["config"]
        feature_cols = list(config.get("feature_cols", []))
        threshold = config.get("threshold")
        thresholds_by_strategy = dict(config.get("thresholds_by_strategy") or {})
        if not thresholds_by_strategy and threshold is not None:
            thresholds_by_strategy["__global__"] = float(threshold)
        data_age_hours = metadata.get("data_age_hours")
        model_age_days = (
            int(float(data_age_hours) // 24)
            if data_age_hours is not None
            else None
        )
        return ModelInfoResponse(
            model_version=metadata.get("model_version"),
            model_status=config.get("model_status"),
            threshold=threshold,
            thresholds_by_strategy=thresholds_by_strategy,
            supported_intervals=list(config.get("supported_intervals") or []),
            supported_strategies=list(config.get("supported_strategies") or []),
            supported_symbols=list(config.get("supported_symbols") or []),
            allow_unseen_symbols=bool(config.get("allow_unseen_symbols", False)),
            supported_exchanges=list(config.get("supported_exchanges") or []),
            feature_schema_version=config.get("feature_schema_version"),
            target_horizon_minutes=config.get("target_horizon_minutes"),
            target_horizon_bars=config.get("target_horizon_bars"),
            minimum_net_return=config.get("minimum_net_return"),
            maximum_target_drawdown=config.get("maximum_target_drawdown"),
            fee=config.get("fee"),
            slippage=config.get("slippage"),
            entry_convention=config.get("entry_convention"),
            exit_convention=config.get("exit_convention"),
            calibration_method=config.get("calibration_method"),
            train_start=config.get("train_start"),
            train_end=config.get("train_end"),
            evaluation_train_end=config.get("evaluation_train_end"),
            evaluation_test_end=config.get("evaluation_test_end"),
            production_train_end=config.get("production_train_end"),
            feature_count=len(feature_cols),
            feature_cols=feature_cols,
            cat_features=list(config.get("cat_features", [])),
            model_file_exists=metadata["model_file_exists"],
            config_file_exists=metadata["config_file_exists"],
            model_age_days=model_age_days,
            data_age_hours=data_age_hours,
            is_model_stale=metadata.get("is_model_stale"),
            warnings=list(metadata.get("compatibility_warnings") or []),
        )
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"could not read model metadata: {error}",
        ) from error

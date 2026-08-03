from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..grpc_client import MLGrpcClient
from ..schemas.ml_schemas import MLpredictresponse, ModelInfoResponse
from ..services.market_services import GetCandles


ml_router = APIRouter(prefix="/ml")
ml_client = MLGrpcClient()


@ml_router.get("/prediction-quality", response_model=MLpredictresponse)
def prediction_quality(
    exchange: Literal["binance", "bybit"] = "binance",
    symbol: str = Query(default="BTCUSDT", min_length=3),
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = "1h",
    strategy_name: Literal["breakout", "mean_reversion"] = "mean_reversion",
    limit: int = Query(default=100, ge=60, le=5000),
):
    try:
        downloader = GetCandles(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        candles = (
            downloader.get_bybit_candles_dc().items
            if exchange == "bybit"
            else downloader.get_binance_candles().items
        )

        if len(candles) < settings.MIN_CANDLES:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"got: {len(candles)}, "
                    f"required: {settings.MIN_CANDLES}"
                ),
            )

        response = ml_client.predict_quality(
            symbol=symbol,
            interval=interval,
            strategy_name=strategy_name,
            candles=candles,
        )

        return MLpredictresponse(
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            strategy_name=strategy_name,
            candles_count=len(candles),
            prob_good_trade=response.prob_good_trade,
            risk_score=response.risk_score,
            trade_allowed=response.trade_allowed,
            threshold=response.threshold,
            risk_level=response.risk_level,
            model_version=response.model_version,
        )
    except HTTPException:
        raise
    except ConnectionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@ml_router.get("/model-info", response_model=ModelInfoResponse)
def get_model_info():
    model_path = Path(settings.MODEL_PATH)
    config_path = Path(settings.MODEL_CONFIG_PATH)

    if not config_path.exists():
        return ModelInfoResponse(
            model_file_exists=model_path.exists(),
            config_file_exists=False,
        )

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        feature_cols = list(config.get("feature_cols", []))
        train_end = config.get("train_end")
        model_age_days: int | None = None
        is_model_stale: bool | None = None

        if train_end:
            parsed = datetime.fromisoformat(str(train_end))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                parsed = parsed.astimezone(timezone.utc)
            model_age_days = max(
                0,
                (datetime.now(timezone.utc) - parsed).days,
            )
            is_model_stale = model_age_days > settings.MODEL_MAX_AGE_DAYS

        return ModelInfoResponse(
            model_version=config.get("model_version"),
            threshold=config.get("threshold"),
            train_start=config.get("train_start"),
            train_end=train_end,
            feature_count=len(feature_cols),
            feature_cols=feature_cols,
            cat_features=list(config.get("cat_features", [])),
            model_file_exists=model_path.exists(),
            config_file_exists=True,
            model_age_days=model_age_days,
            is_model_stale=is_model_stale,
        )
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"could not read model config: {error}",
        ) from error

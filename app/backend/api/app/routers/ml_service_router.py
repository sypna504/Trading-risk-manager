from ..config import settings
import grpc
from fastapi import APIRouter, HTTPException, Query
from ..services.market_services import GetCandles, Candle, Candles
from typing import Literal
from ..grpc_client import MLGrpcClient
from ..schemas.ml_schemas import MLpredictresponse


ml_service = MLGrpcClient(
    address=f"127.0.0.1:{settings.ML_SERVICE_PORT}"
)

ml_router = APIRouter(prefix="/ml")
ml_client = MLGrpcClient()


@ml_router.get("/prediction-quality", response_model=MLpredictresponse)
def prediction_quality(
    exchange: Literal[
        "binance",
        "bybit",
    ] = "binance",
    symbol: str = Query(
        default="BTCUSDT",
        min_length=3,
    ),
    interval: Literal[
        "1m",
        "5m",
        "15m",
        "1h",
        "4h",
        "1d",
    ] = "1h",
    strategy_name: Literal[
        "breakout",
        "mean_reversion",
    ] = "mean_reversion",
    limit: int = Query(
        default=100,
        ge=60,
        le=5000,
    ),
    ):

    downloader = GetCandles(symbol=symbol,interval=interval, limit=limit,)
    exchange_name = exchange.lower()

    try:
        if exchange_name=="bybit":
            candles = downloader.get_bybit_candles_dc().items

        if exchange_name == "binance":
            candles = downloader.get_binance_candles().items

        if len(candles)<60:
            raise HTTPException(status_code=502, detail=f"got:{len(candles)}, required:{settings.MIN_CANDLES}")
        
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
    
    except ConnectionError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    

    
        


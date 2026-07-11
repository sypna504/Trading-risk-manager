from ..config import settings
import grpc
from fastapi import APIRouter, HTTPException
from ..services.market_services import GetCandles, Candle, Candles
from ..grpc_client import MLService

ml_service = MLService(
    address=f"127.0.0.1:{settings.ML_SERVICE_PORT}"
)

ml_router = APIRouter(prefix="/ml")

@ml_router.get("/prediction_quality")
def prediction_quality(
    symbol,
    interval,
    strategy,
    exchange,
    limit,
    action,
    features):

    downloader = GetCandles(symbol=symbol,interval=interval, limit=limit,)
    exchange_name = exchange.lower()

    try:
        if exchange_name=="bybit":
            candles = downloader.get_bybit_candles_dc()

        if exchange_name == "binance":
            candles = downloader.get_binance_candles()

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    candles_list = candles.items if hasattr(candles, 'items') else candles
    

    
        


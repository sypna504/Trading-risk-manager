from fastapi import APIRouter, HTTPException
from ..services.market_services import GetCandles
from ..schemas.market_schemas import CandlesListResponce

market_router = APIRouter(prefix="/market")

@market_router.get("/candles", 
            response_model=CandlesListResponce,
            summary="get candles list",
            description="Возвращает исторические свечи для указанной биржи и торговой пары"
            )
async def get_market_candles(exchange: str="binance", symbol:str="BTCUSD", interval:str="1h", limit: int=1000):
    downloader = GetCandles(symbol=symbol, interval=interval, limit=limit)
    exchange_name = exchange.lower()
    try:
        if exchange_name=="bybit":
            candles = downloader.get_bybit_candles_dc()

        if exchange_name == "binance":
            candles = downloader.get_binance_candles()
    
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    candles_list = candles.items if hasattr(candles, 'items') else candles
    responce = {
        "exchange": exchange_name,
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
        "candles": candles_list
    }
    return responce
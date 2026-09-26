from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..schemas.market_schemas import CandlesListResponce
from ..services.market_services import GetCandles


market_router = APIRouter(prefix="/market")


@market_router.get(
    "/candles",
    response_model=CandlesListResponce,
    summary="get candles list",
    description=(
        "Возвращает исторические свечи для указанной биржи "
        "и торговой пары"
    ),
)
async def get_market_candles(
    exchange: Literal["binance", "bybit"] = "binance",
    symbol: str = Query(default="BTCUSDT", min_length=3),
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = "1h",
    limit: int = Query(default=1000, ge=1, le=5000),
):
    try:
        downloader = GetCandles(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        candles = (
            downloader.get_bybit_candles_dc()
            if exchange == "bybit"
            else downloader.get_binance_candles()
        )

        return {
            "exchange": exchange,
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "candles": candles.items,
        }
    except ConnectionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

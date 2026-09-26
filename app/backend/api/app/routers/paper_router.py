from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query

from app.paper.metrics import paper_metrics
from app.paper.repository import PaperRepository
from app.paper.service import PaperTradingService

from ..config import settings
from ..services.market_services import GetCandles
from ..storage.decision_repository import DecisionRepository

router = APIRouter(prefix="/paper", tags=["paper"])
repository = PaperRepository(settings.DATABASE_PATH)
service = PaperTradingService(repository)
decisions = DecisionRepository()

@router.get("/portfolio")
def get_portfolio(): return repository.get_portfolio()
@router.get("/positions")
def get_positions(): return repository.list_positions()
@router.get("/positions/open")
def get_open_positions(): return repository.list_positions(open_only=True)
@router.get("/positions/{position_id}")
def get_position(position_id: str):
    position=repository.get_position(position_id)
    if position is None: raise HTTPException(status_code=404,detail="paper position not found")
    return position
@router.get("/equity")
def get_equity(): return repository.equity_curve()
@router.get("/metrics")
def get_metrics(): return paper_metrics(repository)

def _download(position, limit: int = 500) -> list[dict]:
    downloader=GetCandles(symbol=position.symbol, interval=position.interval, limit=limit)
    items=(downloader.get_bybit_candles_dc().items if position.exchange=="bybit" else downloader.get_binance_candles().items)
    return [{"timestamp":c.timestamp,"open":c.open,"high":c.high,"low":c.low,"close":c.close,"volume":c.volume} for c in items]

def _decision_payload(row: dict) -> dict:
    return {
        **row,
        "risk_parameters": {
            "recommended_position_notional": row.get("position_notional") or 0.0,
            "stop_loss_price": row.get("stop_loss_price"),
            "take_profit_price": row.get("take_profit_price"),
        },
        "news_context": {
            "available": bool(row.get("news_context_available")),
            "risk_level": row.get("news_risk_level"),
            "news_count": row.get("news_count",0),
            "high_impact_count": row.get("high_impact_news_count",0),
        },
    }

@router.post("/evaluate")
def evaluate_positions(limit: int = Query(default=100, ge=1, le=500)):
    opened=0
    # Paper execution is downstream from the frozen decision gate. It never
    # re-scores the model or changes trade_allowed.
    for row in reversed(decisions.list(limit=limit, trade_allowed=True)):
        if repository.get_by_decision(int(row["id"])) is not None:
            continue
        if not row.get("signal_timestamp"):
            continue
        try:
            signal_time=datetime.fromisoformat(str(row["signal_timestamp"]).replace("Z","+00:00"))
            candles=GetCandles(symbol=row["symbol"], interval=row["interval"], limit=500)
            items=(candles.get_bybit_candles_dc().items if row.get("exchange")=="bybit" else candles.get_binance_candles().items)
            next_bar=next((c for c in items if c.timestamp > signal_time), None)
            if next_bar is None:
                continue
            position=service.open_from_decision(_decision_payload(row), {"timestamp":next_bar.timestamp,"open":next_bar.open,"high":next_bar.high,"low":next_bar.low,"close":next_bar.close})
            opened += int(position is not None)
        except Exception:
            continue
    result=service.evaluate_all(lambda position:_download(position))
    return {**result,"opened":opened,"mode":"paper_only","real_trading":False}

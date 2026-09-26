from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import PositionStatus
from .repository import PaperRepository


def _part_metrics(positions):
    closed=[p for p in positions if p.status==PositionStatus.CLOSED and p.realized_pnl is not None]
    pnl=[float(p.realized_pnl) for p in closed];wins=[x for x in pnl if x>0];losses=[x for x in pnl if x<0]
    gp=sum(wins);gl=-sum(losses)
    return {"trade_count":len(closed),"profit_factor":gp/gl if gl else (float("inf") if gp else None),"win_rate":len(wins)/len(closed) if closed else None,"average_win":sum(wins)/len(wins) if wins else None,"average_loss":sum(losses)/len(losses) if losses else None,"realized_pnl":sum(pnl)}

def paper_metrics(repository: PaperRepository) -> dict:
    positions=repository.list_positions(limit=5000);portfolio=repository.get_portfolio();base=_part_metrics(positions);now=datetime.now(timezone.utc)
    def window(days:int):
        cutoff=now-timedelta(days=days);part=[]
        for p in positions:
            if p.exit_at and p.exit_at>=cutoff: part.append(p)
        return _part_metrics(part)
    return {
        "paper_return":((portfolio.current_equity/portfolio.starting_balance)-1) if portfolio else None,
        "max_drawdown":portfolio.max_drawdown if portfolio else None,
        "exposure":portfolio.gross_exposure if portfolio else 0.0,
        **base,"rolling_7d":window(7),"rolling_30d":window(30),
    }

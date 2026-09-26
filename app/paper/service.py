from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import ExitReason, PaperPortfolio, PaperRiskConfig, PositionStatus, VirtualPosition
from .repository import PaperRepository


class PaperTradingService:
    def __init__(self, repository: PaperRepository, risk: PaperRiskConfig | None = None) -> None:
        self.repository = repository
        self.risk = risk or PaperRiskConfig()

    def _portfolio(self) -> PaperPortfolio:
        portfolio = self.repository.get_portfolio()
        if portfolio is None:
            raise RuntimeError("paper portfolio is not initialized")
        return portfolio

    def open_from_decision(self, decision: dict, next_bar: dict) -> VirtualPosition | None:
        if not bool(decision.get("trade_allowed")) or not bool(decision.get("signal_detected")):
            return None
        decision_id = int(decision["id"])
        existing = self.repository.get_by_decision(decision_id)
        if existing is not None:
            return existing
        if str(decision.get("entry_convention")) != "next_bar_open":
            raise ValueError("paper entry requires next_bar_open production contract")

        portfolio = self._portfolio()
        open_positions = self.repository.list_positions(open_only=True)
        if len(open_positions) >= self.risk.max_concurrent_positions:
            return None

        risk_parameters = decision.get("risk_parameters") or {}
        requested_notional = float(risk_parameters.get("recommended_position_notional") or 0.0)
        max_notional = portfolio.current_equity * self.risk.max_position_share_pct / 100.0
        notional = min(requested_notional, max_notional)
        current_exposure = sum(position.notional for position in open_positions if position.status == PositionStatus.OPEN)
        if current_exposure + notional > portfolio.current_equity * self.risk.max_gross_exposure_pct / 100.0:
            return None
        stop_loss = float(risk_parameters["stop_loss_price"])
        take_profit = float(risk_parameters["take_profit_price"])
        risk_amount = max(0.0, notional * abs(float(decision["planned_entry_price"]) - stop_loss) / float(decision["planned_entry_price"]))
        if risk_amount > portfolio.current_equity * self.risk.max_risk_per_trade_pct / 100.0:
            return None
        open_risk = sum(position.risk_amount for position in open_positions if position.status == PositionStatus.OPEN)
        if open_risk + risk_amount > portfolio.current_equity * self.risk.max_portfolio_risk_pct / 100.0:
            return None

        raw_entry = float(next_bar["open"])
        entry = raw_entry * (1.0 + self.risk.default_slippage)
        quantity = notional / entry if entry else 0.0
        timeout_bars = int(decision.get("target_horizon_bars") or 3)
        bar_minutes = int(decision.get("target_horizon_minutes") or 180) // max(timeout_bars, 1)
        opened_at = next_bar["timestamp"]
        if isinstance(opened_at, str):
            opened_at = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        position = VirtualPosition(
            symbol=str(decision["symbol"]), exchange=str(decision.get("exchange") or "binance"), interval=str(decision.get("interval") or "1h"), strategy=str(decision.get("selected_strategy") or "unknown"),
            model_version=str(decision.get("model_version") or "unknown"), decision_id=decision_id,
            opened_at=opened_at, planned_entry=float(decision["planned_entry_price"]), realized_virtual_entry=entry,
            quantity=quantity, notional=notional, stop_loss=stop_loss, take_profit=take_profit,
            timeout_at=opened_at + timedelta(minutes=bar_minutes * timeout_bars), fee=self.risk.default_fee,
            slippage=self.risk.default_slippage, status=PositionStatus.OPEN, risk_amount=risk_amount,
            news_snapshot=decision.get("news_context"),
        )
        self.repository.save_position(position)
        self._revalue(open_positions=[*open_positions, position])
        return position

    def evaluate_position(self, position: VirtualPosition, candles: list[dict]) -> VirtualPosition:
        if position.status != PositionStatus.OPEN:
            return position
        entry = float(position.realized_virtual_entry or position.planned_entry)
        for candle in candles:
            timestamp = candle["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            if position.opened_at and timestamp < position.opened_at:
                continue
            high, low, close = float(candle["high"]), float(candle["low"]), float(candle["close"])
            hit_sl = low <= position.stop_loss
            hit_tp = high >= position.take_profit
            reason = None
            exit_price = None
            if hit_sl and hit_tp:
                reason = ExitReason.STOP_LOSS if self.risk.intrabar_priority == "stop_loss" else ExitReason.TAKE_PROFIT
                exit_price = position.stop_loss if reason == ExitReason.STOP_LOSS else position.take_profit
            elif hit_sl:
                reason, exit_price = ExitReason.STOP_LOSS, position.stop_loss
            elif hit_tp:
                reason, exit_price = ExitReason.TAKE_PROFIT, position.take_profit
            elif timestamp >= position.timeout_at:
                reason, exit_price = ExitReason.TIMEOUT, close
            if reason is None:
                continue
            # Long-only MVP: exit slippage is adverse, and fees are charged on entry+exit notionals.
            exit_after_slippage = float(exit_price) * (1.0 - position.slippage)
            gross = position.quantity * (exit_after_slippage - entry)
            fees = position.fee * (position.notional + position.quantity * exit_after_slippage)
            pnl = gross - fees
            updated = position.model_copy(update={
                "status": PositionStatus.CLOSED, "exit_at": timestamp, "exit_price": exit_after_slippage,
                "exit_reason": reason, "realized_pnl": pnl,
                "return_pct": pnl / position.notional if position.notional else 0.0,
            })
            self.repository.save_position(updated)
            self._close_in_portfolio(updated)
            return updated
        return position

    def evaluate_all(self, candle_provider) -> dict[str, int]:
        checked = closed = 0
        mark_prices: dict[str, float] = {}
        for position in self.repository.list_positions(open_only=True):
            if position.status != PositionStatus.OPEN:
                continue
            checked += 1
            candles = candle_provider(position)
            updated = self.evaluate_position(position, candles)
            closed += int(updated.status == PositionStatus.CLOSED)
            if updated.status == PositionStatus.OPEN and candles:
                mark_prices[updated.id] = float(candles[-1]["close"])
        self.mark_to_market(mark_prices)
        return {"checked": checked, "closed": closed}

    def mark_to_market(self, prices_by_position: dict[str, float]) -> PaperPortfolio:
        portfolio = self._portfolio()
        positions = [p for p in self.repository.list_positions(open_only=True) if p.status == PositionStatus.OPEN]
        gross_entry = sum(p.notional for p in positions)
        market_value = 0.0
        for position in positions:
            price = float(prices_by_position.get(position.id, position.realized_virtual_entry or position.planned_entry))
            market_value += position.quantity * price
        cash = portfolio.starting_balance + portfolio.realized_pnl - gross_entry
        unrealized = market_value - gross_entry
        equity = cash + market_value
        peak = max(portfolio.peak_equity, equity)
        drawdown = equity / peak - 1 if peak else 0.0
        updated = portfolio.model_copy(update={
            "cash": cash, "gross_exposure": gross_entry,
            "open_risk": sum(p.risk_amount for p in positions),
            "unrealized_pnl": unrealized, "current_equity": equity,
            "peak_equity": peak, "max_drawdown": min(portfolio.max_drawdown, drawdown),
            "updated_at": datetime.now(timezone.utc),
        })
        self.repository.save_portfolio(updated)
        return updated

    def _close_in_portfolio(self, position: VirtualPosition) -> None:
        portfolio = self._portfolio()
        realized = portfolio.realized_pnl + float(position.realized_pnl or 0.0)
        equity = portfolio.starting_balance + realized
        peak = max(portfolio.peak_equity, equity)
        drawdown = equity / peak - 1 if peak else 0.0
        open_positions = [p for p in self.repository.list_positions(open_only=True) if p.id != position.id and p.status == PositionStatus.OPEN]
        open_notional = sum(p.notional for p in open_positions)
        updated = portfolio.model_copy(update={
            "current_equity": equity, "cash": equity - open_notional, "realized_pnl": realized,
            "unrealized_pnl": 0.0, "gross_exposure": open_notional,
            "open_risk": sum(p.risk_amount for p in open_positions), "peak_equity": peak,
            "max_drawdown": min(portfolio.max_drawdown, drawdown), "updated_at": datetime.now(timezone.utc),
        })
        self.repository.save_portfolio(updated)

    def _revalue(self, open_positions: list[VirtualPosition] | None = None) -> None:
        portfolio = self._portfolio()
        positions = open_positions if open_positions is not None else self.repository.list_positions(open_only=True)
        gross = sum(p.notional for p in positions if p.status == PositionStatus.OPEN)
        updated = portfolio.model_copy(update={
            "gross_exposure": gross,
            "open_risk": sum(p.risk_amount for p in positions if p.status == PositionStatus.OPEN),
            "cash": portfolio.starting_balance + portfolio.realized_pnl - gross,
            "current_equity": portfolio.starting_balance + portfolio.realized_pnl,
            "unrealized_pnl": 0.0,
            "updated_at": datetime.now(timezone.utc),
        })
        self.repository.save_portfolio(updated)

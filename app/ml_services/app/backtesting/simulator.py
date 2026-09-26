from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class OpenPosition:
    exit_time: pd.Timestamp
    risk_amount: float
    notional: float
    pnl: float
    holding_bars: int


def _interval_delta(interval: str) -> pd.Timedelta:
    value = interval.strip().lower()
    if len(value) < 2:
        raise ValueError(f"invalid interval: {interval}")
    amount = int(value[:-1])
    unit = value[-1]
    if amount <= 0 or unit not in {"m", "h", "d"}:
        raise ValueError(f"invalid interval: {interval}")
    return {
        "m": pd.Timedelta(minutes=amount),
        "h": pd.Timedelta(hours=amount),
        "d": pd.Timedelta(days=amount),
    }[unit]


def _threshold_for(row: pd.Series, thresholds: dict[str, float] | float) -> float:
    if isinstance(thresholds, dict):
        strategy = str(row.get("strategy_name", ""))
        return float(thresholds.get(strategy, thresholds.get("__global__", 0.5)))
    return float(thresholds)


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def _regular_returns(
    equity_events: list[tuple[pd.Timestamp, float]],
    start: pd.Timestamp,
    end: pd.Timestamp,
    delta: pd.Timedelta,
    starting_capital: float,
) -> pd.Series:
    if end < start:
        return pd.Series(dtype=float)
    index = pd.date_range(start=start, end=end, freq=delta)
    realized = pd.Series(0.0, index=index)
    previous_equity = starting_capital
    for timestamp, equity in sorted(equity_events, key=lambda item: item[0]):
        bucket = timestamp.floor(delta)
        if bucket not in realized.index:
            continue
        realized.loc[bucket] += (equity - previous_equity) / max(previous_equity, 1e-12)
        previous_equity = equity
    return realized


def run_portfolio_backtest(
    frame: pd.DataFrame,
    probabilities: np.ndarray | None,
    thresholds: dict[str, float] | float,
    *,
    interval: str,
    starting_capital: float = 10_000.0,
    risk_per_trade_pct: float = 1.0,
    max_position_share_pct: float = 25.0,
    max_concurrent_positions: int = 5,
    max_portfolio_risk_pct: float = 5.0,
    max_gross_exposure_pct: float = 100.0,
    base_round_trip_cost: float = 0.003,
    cost_multiplier: float = 1.0,
    trade_all_signals: bool = False,
) -> dict[str, Any]:
    """Event-driven long-only research backtest with overlapping positions.

    This simulator uses realized entry/exit paths already constructed by the
    target builder, while sizing each trade from portfolio equity and stop risk.
    It is intentionally conservative: no leverage and no mark-to-market reuse of
    capital before a position exits.
    """
    if starting_capital <= 0:
        raise ValueError("starting_capital must be positive")
    if cost_multiplier <= 0:
        raise ValueError("cost_multiplier must be positive")
    if frame.empty:
        return {
            "starting_capital": starting_capital,
            "ending_capital": starting_capital,
            "portfolio_return": 0.0,
            "trades": 0,
            "skipped_capacity": 0,
            "profit_factor": None,
            "maximum_drawdown": 0.0,
            "sharpe": None,
            "sortino": None,
            "calmar": None,
            "cagr": None,
            "turnover": 0.0,
            "exposure": 0.0,
            "average_holding_bars": None,
        }

    df = frame.copy().reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if probabilities is None:
        probabilities = np.ones(len(df), dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    if len(probabilities) != len(df):
        raise ValueError("probability length mismatch")
    df["_probability"] = probabilities
    if not trade_all_signals:
        mask = [
            float(row["_probability"]) >= _threshold_for(row, thresholds)
            for _, row in df.iterrows()
        ]
        df = df[np.asarray(mask, dtype=bool)].copy()

    if df.empty:
        return {
            "starting_capital": float(starting_capital),
            "ending_capital": float(starting_capital),
            "portfolio_return": 0.0,
            "trades": 0,
            "skipped_capacity": 0,
            "win_rate": None,
            "mean_trade_pnl": None,
            "profit_factor": None,
            "maximum_drawdown": 0.0,
            "sharpe": None,
            "sortino": None,
            "calmar": None,
            "cagr": 0.0,
            "turnover": 0.0,
            "exposure": 0.0,
            "average_holding_bars": None,
            "maximum_simultaneous_positions": 0,
        }

    delta = _interval_delta(interval)
    df = df.sort_values(["timestamp", "symbol", "strategy_name"]).reset_index(drop=True)
    equity = float(starting_capital)
    open_positions: list[OpenPosition] = []
    equity_events: list[tuple[pd.Timestamp, float]] = []
    trade_pnls: list[float] = []
    notionals: list[float] = []
    holdings: list[int] = []
    skipped_capacity = 0
    exposure_bar_notional = 0.0
    total_bar_capacity = 0.0

    def close_due(until: pd.Timestamp) -> None:
        nonlocal equity, open_positions
        due = sorted(
            [position for position in open_positions if position.exit_time <= until],
            key=lambda position: position.exit_time,
        )
        for position in due:
            equity += position.pnl
            equity_events.append((position.exit_time, equity))
            trade_pnls.append(position.pnl)
            open_positions.remove(position)

    for _, row in df.iterrows():
        signal_time = pd.Timestamp(row["timestamp"])
        entry_time = signal_time + delta
        close_due(entry_time)
        if equity <= 0:
            break
        if len(open_positions) >= max_concurrent_positions:
            skipped_capacity += 1
            continue

        stop_fraction = row.get("stop_loss_fraction")
        if stop_fraction is None or not math.isfinite(float(stop_fraction)) or float(stop_fraction) <= 0:
            skipped_capacity += 1
            continue
        stop_fraction = float(stop_fraction)
        current_risk = sum(position.risk_amount for position in open_positions)
        risk_budget = equity * max_portfolio_risk_pct / 100.0
        trade_risk = min(equity * risk_per_trade_pct / 100.0, max(risk_budget - current_risk, 0.0))
        if trade_risk <= 0:
            skipped_capacity += 1
            continue

        risk_notional = trade_risk / stop_fraction
        per_trade_cap = equity * max_position_share_pct / 100.0
        current_notional = sum(position.notional for position in open_positions)
        gross_cap = equity * max_gross_exposure_pct / 100.0
        available_gross = max(gross_cap - current_notional, 0.0)
        notional = min(risk_notional, per_trade_cap, available_gross)
        if notional <= 0:
            skipped_capacity += 1
            continue

        entry = float(row["entry_price"])
        exit_price = float(row["exit_price"])
        gross_return = exit_price / entry - 1.0
        net_return = gross_return - base_round_trip_cost * cost_multiplier
        pnl = notional * net_return
        holding_bars = max(int(round(float(row.get("holding_bars", 1) or 1))), 1)
        exit_time = entry_time + delta * holding_bars
        actual_risk = notional * stop_fraction
        open_positions.append(
            OpenPosition(
                exit_time=exit_time,
                risk_amount=actual_risk,
                notional=notional,
                pnl=pnl,
                holding_bars=holding_bars,
            )
        )
        notionals.append(notional)
        holdings.append(holding_bars)
        exposure_bar_notional += notional * holding_bars
        total_bar_capacity += equity * holding_bars

    close_due(pd.Timestamp.max.tz_localize(None) if df["timestamp"].dt.tz is None else pd.Timestamp.max.tz_localize("UTC"))
    ending_capital = equity
    portfolio_return = ending_capital / starting_capital - 1.0
    wins = [pnl for pnl in trade_pnls if pnl > 0]
    losses = [pnl for pnl in trade_pnls if pnl < 0]
    profit_factor = sum(wins) / abs(sum(losses)) if losses else (float("inf") if wins else None)

    event_equity = pd.Series(
        [starting_capital, *[value for _, value in equity_events]],
        index=[df["timestamp"].min(), *[timestamp for timestamp, _ in equity_events]],
        dtype=float,
    ).sort_index()
    maximum_drawdown = _max_drawdown(event_equity)
    start = pd.Timestamp(df["timestamp"].min())
    end = max([timestamp for timestamp, _ in equity_events], default=pd.Timestamp(df["timestamp"].max()))
    regular_returns = _regular_returns(equity_events, start, end, delta, starting_capital)
    periods_per_year = pd.Timedelta(days=365) / delta
    std = float(regular_returns.std()) if len(regular_returns) > 1 else 0.0
    mean = float(regular_returns.mean()) if len(regular_returns) else 0.0
    sharpe = mean / std * math.sqrt(float(periods_per_year)) if std > 0 else None
    downside = regular_returns[regular_returns < 0]
    downside_std = float(downside.std()) if len(downside) > 1 else 0.0
    sortino = mean / downside_std * math.sqrt(float(periods_per_year)) if downside_std > 0 else None
    elapsed_years = max((end - start).total_seconds() / (365.0 * 24 * 3600), 1 / 365.0)
    cagr = (ending_capital / starting_capital) ** (1.0 / elapsed_years) - 1.0 if ending_capital > 0 else -1.0
    calmar = cagr / abs(maximum_drawdown) if maximum_drawdown < 0 else None
    turnover = sum(notionals) / starting_capital
    exposure = exposure_bar_notional / total_bar_capacity if total_bar_capacity > 0 else 0.0

    return {
        "starting_capital": float(starting_capital),
        "ending_capital": float(ending_capital),
        "portfolio_return": float(portfolio_return),
        "trades": len(trade_pnls),
        "skipped_capacity": int(skipped_capacity),
        "win_rate": float(np.mean([pnl > 0 for pnl in trade_pnls])) if trade_pnls else None,
        "mean_trade_pnl": float(np.mean(trade_pnls)) if trade_pnls else None,
        "profit_factor": float(profit_factor) if profit_factor is not None and math.isfinite(profit_factor) else profit_factor,
        "maximum_drawdown": float(maximum_drawdown),
        "sharpe": float(sharpe) if sharpe is not None else None,
        "sortino": float(sortino) if sortino is not None else None,
        "calmar": float(calmar) if calmar is not None else None,
        "cagr": float(cagr),
        "turnover": float(turnover),
        "exposure": float(exposure),
        "average_holding_bars": float(np.mean(holdings)) if holdings else None,
        "cost_multiplier": float(cost_multiplier),
        "base_round_trip_cost": float(base_round_trip_cost),
        "max_concurrent_positions": int(max_concurrent_positions),
        "max_portfolio_risk_pct": float(max_portfolio_risk_pct),
        "max_gross_exposure_pct": float(max_gross_exposure_pct),
    }

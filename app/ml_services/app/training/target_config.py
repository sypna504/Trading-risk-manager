from __future__ import annotations

from dataclasses import asdict, dataclass


INTERVAL_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


def interval_to_minutes(interval: str) -> int:
    try:
        return INTERVAL_MINUTES[interval]
    except KeyError as error:
        raise ValueError(f"unsupported interval: {interval}") from error


def horizon_bars(target_horizon_minutes: int, interval: str) -> int:
    if target_horizon_minutes <= 0:
        raise ValueError("target_horizon_minutes must be positive")
    minutes = interval_to_minutes(interval)
    if target_horizon_minutes % minutes != 0:
        raise ValueError(
            "target horizon must be exactly divisible by candle duration: "
            f"horizon={target_horizon_minutes}, interval={interval}"
        )
    bars = target_horizon_minutes // minutes
    if bars < 1:
        raise ValueError("target horizon must contain at least one bar")
    return bars


@dataclass(frozen=True, slots=True)
class TargetConfig:
    target_horizon_minutes: int
    interval: str
    minimum_net_return: float
    maximum_drawdown: float
    fee: float
    slippage: float
    entry_convention: str = "next_bar_open"
    exit_convention: str = "horizon_bar_close"

    @property
    def target_horizon_bars(self) -> int:
        return horizon_bars(self.target_horizon_minutes, self.interval)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["target_horizon_bars"] = self.target_horizon_bars
        return result


def physical_purge(target_horizon_minutes: int, embargo_minutes: int = 0):
    """Return the physical purge/embargo duration used by every time split."""
    if target_horizon_minutes <= 0:
        raise ValueError("target_horizon_minutes must be positive")
    if embargo_minutes < 0:
        raise ValueError("embargo_minutes must not be negative")
    import pandas as pd

    return pd.Timedelta(minutes=target_horizon_minutes + embargo_minutes)

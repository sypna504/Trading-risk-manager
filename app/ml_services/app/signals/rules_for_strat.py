from __future__ import annotations

from typing import Any

import pandas as pd


STRATEGIES = ["breakout", "mean_reversion"]
# Backward-compatible alias for the original misspelled constant.
STRATAGIES = STRATEGIES


class Strategies:
    """Compatibility helper for explicit strategy checks.

    The production feature builder remains the source of truth for signal
    columns. This helper only evaluates an already calculated feature row.
    """

    def __init__(self, row: pd.Series | dict[str, Any]):
        self.row = row

    def determine_strategies(self) -> list[str]:
        active: list[str] = []
        if (
            float(self.row["close"]) > float(self.row["high_20"])
            and float(self.row["volume_z_20"]) > 0.5
        ):
            active.append("breakout")
        if (
            float(self.row["rsi_14"]) < 35
            and float(self.row["price_z_20"]) < -1
        ):
            active.append("mean_reversion")
        return active

    def determine_strategy(self) -> str | None:
        active = self.determine_strategies()
        return active[0] if active else None

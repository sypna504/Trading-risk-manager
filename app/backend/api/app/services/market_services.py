from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import ccxt
import pandas as pd

from ..config import settings


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Candles:
    symbol: str
    interval: str
    items: list[Candle] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        if not self.items:
            return pd.DataFrame()
        return pd.DataFrame([candle.__dict__ for candle in self.items])


class GetCandles:
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        limit: int = 100,
    ) -> None:
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")

        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol is required")
        if "/" not in normalized_symbol and normalized_symbol.endswith("USDT"):
            self.symbol = normalized_symbol[:-4] + "/" + normalized_symbol[-4:]
        else:
            self.symbol = normalized_symbol

        self.interval = interval
        self.limit = limit
        timeout_ms = int(settings.REQUEST_TIMEOUT * 1000)

        self.binance_exchange = ccxt.binance(
            {
                "enableRateLimit": True,
                "timeout": timeout_ms,
            }
        )
        self.bybit_exchange = ccxt.bybit(
            {
                "enableRateLimit": True,
                "timeout": timeout_ms,
            }
        )

    @staticmethod
    def _convert_rows(raw_candles: list, exchange_name: str) -> list[Candle]:
        candle_list: list[Candle] = []

        for row in raw_candles:
            if not isinstance(row, (list, tuple)) or len(row) < 6:
                raise ValueError(
                    f"Invalid candle format from {exchange_name}: {row}"
                )

            timestamp_ms = int(row[0])
            values = [float(value) for value in row[1:6]]
            if timestamp_ms <= 0:
                raise ValueError("candle timestamp must be positive")
            if not all(math.isfinite(value) for value in values):
                raise ValueError("OHLCV values must be finite")

            candle = Candle(
                timestamp=datetime.fromtimestamp(
                    timestamp_ms / 1000,
                    tz=timezone.utc,
                ),
                open=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
                volume=values[4],
            )

            if min(candle.open, candle.high, candle.low, candle.close) <= 0:
                raise ValueError("OHLC values must be positive")
            if candle.volume < 0:
                raise ValueError("volume must be non-negative")
            if candle.high < max(candle.open, candle.close, candle.low):
                raise ValueError("high is lower than another OHLC value")
            if candle.low > min(candle.open, candle.close, candle.high):
                raise ValueError("low is higher than another OHLC value")

            candle_list.append(candle)

        return candle_list

    def _download(self, exchange, exchange_name: str, params: dict | None = None) -> Candles:
        timeframe_ms = int(exchange.parse_timeframe(self.interval) * 1000)
        if timeframe_ms <= 0:
            raise ValueError(f"invalid timeframe: {self.interval}")

        now_ms = int(exchange.milliseconds())
        current_open_ms = now_ms // timeframe_ms * timeframe_ms
        requested_rows = self.limit + 2
        since = current_open_ms - requested_rows * timeframe_ms
        raw_candles: list = []
        last_timestamp: int | None = None

        while len(raw_candles) < requested_rows:
            step_limit = min(1000, requested_rows - len(raw_candles))

            try:
                response = exchange.fetch_ohlcv(
                    self.symbol,
                    self.interval,
                    since,
                    step_limit,
                    params=params or {},
                )
            except Exception as error:
                raise ConnectionError(
                    f"Network error while requesting {exchange_name} "
                    f"for {self.symbol}: {error}"
                ) from error

            if not response:
                break

            current_last_timestamp = int(response[-1][0])
            if last_timestamp is not None and current_last_timestamp <= last_timestamp:
                break

            raw_candles.extend(response)
            last_timestamp = current_last_timestamp
            since = current_last_timestamp + timeframe_ms
            if getattr(exchange, "rateLimit", 0):
                time.sleep(float(exchange.rateLimit) / 1000)

        if not raw_candles:
            raise ValueError(
                f"{exchange_name} returned an empty candle list "
                f"for {self.symbol}"
            )

        # CCXT commonly returns the currently forming candle. It must not be
        # used by signal detection or inference.
        by_timestamp: dict[int, list | tuple] = {}
        for row in raw_candles:
            if not isinstance(row, (list, tuple)) or len(row) < 6:
                raise ValueError(
                    f"Invalid candle format from {exchange_name}: {row}"
                )
            timestamp_ms = int(row[0])
            if timestamp_ms < current_open_ms:
                by_timestamp[timestamp_ms] = row

        closed_rows = [by_timestamp[key] for key in sorted(by_timestamp)]
        closed_rows = closed_rows[-self.limit :]
        if not closed_rows:
            raise ValueError(
                f"{exchange_name} returned no closed candles for {self.symbol}"
            )

        return Candles(
            symbol=self.symbol,
            interval=self.interval,
            items=self._convert_rows(closed_rows, exchange_name),
        )

    def get_binance_candles(self) -> Candles:
        return self._download(self.binance_exchange, "Binance")

    def get_bybit_candles_dc(self) -> Candles:
        return self._download(
            self.bybit_exchange,
            "Bybit",
            params={"category": "spot"},
        )

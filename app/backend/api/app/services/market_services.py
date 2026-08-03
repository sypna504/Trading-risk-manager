from __future__ import annotations

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

        if "/" not in symbol and symbol.upper().endswith("USDT"):
            normalized = symbol.upper()
            self.symbol = normalized[:-4] + "/" + normalized[-4:]
        else:
            self.symbol = symbol.upper()

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

            candle = Candle(
                timestamp=datetime.fromtimestamp(
                    int(row[0]) / 1000,
                    tz=timezone.utc,
                ),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )

            if min(candle.open, candle.high, candle.low, candle.close) <= 0:
                raise ValueError("OHLC values must be positive")
            if candle.volume < 0:
                raise ValueError("volume must be non-negative")
            if candle.high < max(candle.open, candle.close):
                raise ValueError("high is lower than open or close")
            if candle.low > min(candle.open, candle.close):
                raise ValueError("low is higher than open or close")

            candle_list.append(candle)

        return candle_list

    def _download(self, exchange, exchange_name: str, params: dict | None = None) -> Candles:
        timeframe_ms = exchange.parse_timeframe(self.interval) * 1000
        since = exchange.milliseconds() - self.limit * timeframe_ms
        raw_candles: list = []
        last_timestamp: int | None = None

        while len(raw_candles) < self.limit:
            step_limit = min(1000, self.limit - len(raw_candles))

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
            if last_timestamp == current_last_timestamp:
                break

            raw_candles.extend(response)
            last_timestamp = current_last_timestamp
            since = current_last_timestamp + timeframe_ms
            time.sleep(exchange.rateLimit / 1000)

        if not raw_candles:
            raise ValueError(
                f"{exchange_name} returned an empty candle list "
                f"for {self.symbol}"
            )

        raw_candles = raw_candles[-self.limit :]
        return Candles(
            symbol=self.symbol,
            interval=self.interval,
            items=self._convert_rows(raw_candles, exchange_name),
        )

    def get_binance_candles(self) -> Candles:
        return self._download(self.binance_exchange, "Binance")

    def get_bybit_candles_dc(self) -> Candles:
        return self._download(
            self.bybit_exchange,
            "Bybit",
            params={"category": "spot"},
        )

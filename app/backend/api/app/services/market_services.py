import ccxt
import time
from dataclasses import dataclass, field
from typing import Annotated
import pandas as pd
from typing import List
from datetime import datetime, timezone

ms = Annotated[int, "ms"]

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
    items: List[Candle] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Метод для мгновенного разворачивания списка в DataFrame"""

        if not self.items:
            return pd.DataFrame()

        data = [c.__dict__ for c in self.items]
        df = pd.DataFrame(data)
        return df

class GetCandles:
    def __init__(self, symbol="BTCUSDT", interval="1h", limit=100):
        if "/" not in symbol and symbol.endswith("USDT"):
            self.symbol = symbol[:-4] + "/" + symbol[-4:]
        else:
            self.symbol = symbol
        self.interval = interval
        self.limit = limit
        
        self.binance_exchange = ccxt.binance({'enableRateLimit': True})
        self.bybit_exchange = ccxt.bybit({'enableRateLimit': True})

    def get_binance_candles(self) -> Candles:
        timeframe_ms = self.binance_exchange.parse_timeframe(self.interval) * 1000
        since = self.binance_exchange.milliseconds() - (self.limit * timeframe_ms)
        
        raw_candles = []
        while len(raw_candles) < self.limit:
            try:
                step_limit = min(1000, self.limit - len(raw_candles))
                response = self.binance_exchange.fetch_ohlcv(self.symbol, self.interval, since, step_limit)
                if not response:
                    break
                raw_candles.extend(response)
                since = response[-1][0] + timeframe_ms
                time.sleep(self.binance_exchange.rateLimit / 1000)
            except Exception as e:
                raise ConnectionError(f"Ошибка сети при запросе к Binance для {self.symbol}: {e}")
                
        if not raw_candles:
            raise ValueError(f"Binance вернул пустой список свечей для {self.symbol}")
        
        raw_candles = raw_candles[-self.limit:]
        candle_list = []
        for row in raw_candles:
            if not isinstance(row, list) or len(row) < 6:
                raise ValueError(f"Некорректный формат свечи в ответе Binance: {row}")
            candle_list.append(
                Candle(
                    timestamp=datetime.fromtimestamp(
                        int(row[0]) / 1000,
                        tz=timezone.utc,
                    ),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5])
                )
            )
        return Candles(symbol=self.symbol, interval=self.interval, items=candle_list)
    
    def get_bybit_candles_dc(self) -> Candles:
        timeframe_ms = self.bybit_exchange.parse_timeframe(self.interval) * 1000
        since = self.bybit_exchange.milliseconds() - (self.limit * timeframe_ms)
        
        raw_candles = []
        while len(raw_candles) < self.limit:
            try:
                step_limit = min(1000, self.limit - len(raw_candles))
                response = self.bybit_exchange.fetch_ohlcv(self.symbol, self.interval, since, step_limit, params={'category': 'spot'})
                if not response:
                    break
                raw_candles.extend(response)
                since = response[-1][0] + timeframe_ms
                time.sleep(self.bybit_exchange.rateLimit / 1000)
            except Exception as e:
                raise ConnectionError(f"Ошибка сети при запросе к Bybit для {self.symbol}: {e}")
        
        if not raw_candles:
            raise ValueError(f"Bybit вернул пустой список свечей для {self.symbol}")
        
        raw_candles = raw_candles[-self.limit:]
        candle_list = []
        for row in raw_candles:
            if not isinstance(row, list) or len(row) < 6:
                raise ValueError(f"Некорректный формат свечи в ответе Bybit: {row}")
            candle_list.append(
                Candle(
                    timestamp=datetime.fromtimestamp(
                        int(row[0]) / 1000,
                        tz=timezone.utc,
                    ),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5])
                )
            )
        return Candles(symbol=self.symbol, interval=self.interval, items=candle_list)
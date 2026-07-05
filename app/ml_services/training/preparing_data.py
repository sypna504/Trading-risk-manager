import requests
from dataclasses import dataclass, field
from typing import Annotated
import pandas as pd
from typing import List
from datetime import datetime

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

        # Превращаем список датаклассов в список словарей и отдаем в Pandas
        data = [c.__dict__ for c in self.items]
        df = pd.DataFrame(data)
        return df

class GetCandles:
    def __init__(self, symbol="BTCUSDT", interval="1h", limit=100):
        self.symbol = symbol
        self.interval = interval
        self.limit = limit

    def get_binance_candles(self) -> Candles:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": self.symbol, "interval": self.interval, "limit": self.limit}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ошибка сети при запросе к Binance: {e}")
            
        data = response.json()
        
        if isinstance(data, dict) and "code" in data:
            raise ValueError(f"Binance API Error: {data.get('msg')} (Code: {data.get('code')})")
            
        if not data:
            raise ValueError(f"Binance вернул пустой список свечей для {self.symbol}")
        
        candle_list = []
        for row in data:
            if not isinstance(row, list) or len(row) < 6:
                raise ValueError(f"Некорректный формат свечи в ответе Binance: {row}")
            candle_list.append(
                Candle(
                    timestamp=datetime.fromtimestamp(int(row[0]) / 1000),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5])
                )
            )
        return Candles(symbol=self.symbol, interval=self.interval, items=candle_list)
    
    def get_bybit_candles_dc(self) -> Candles:
        url = "https://bybit.com"
        params = {"category": "spot", "symbol": self.symbol, "interval": self.interval, "limit": self.limit}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ошибка сети при запросе к Bybit: {e}")
        
        data = response.json()

        if data.get("retCode") != 0:
            raise ValueError(f"Bybit API Error: {data.get('retMsg')} (Code: {data.get('retCode')})")
        
        raw_list = data.get("result", {}).get("list", [])
        if not raw_list:
            raise ValueError(f"Bybit вернул пустой список свечей для {self.symbol}")
        
        
        candle_list = []
        # Bybit отдает от новых к старым, поэтому разворачиваем через [::-1]
        for row in raw_list[::-1]:
            if not isinstance(row, list) or len(row) < 6:
                raise ValueError(f"Некорректный формат свечи в ответе Bybit: {row}")
            candle_list.append(
                Candle(
                    timestamp=datetime.fromtimestamp(int(int(row[0])) / 1000),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5])
                )
            )
        return Candles(symbol=self.symbol, interval=self.interval, items=candle_list)



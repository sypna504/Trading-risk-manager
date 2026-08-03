# Архитектура MVP

## Компоненты

### FastAPI backend

Отвечает за HTTP API, загрузку свечей, поиск сигнала, вызов gRPC, расчёт риска, SQLite и web-интерфейс.

### Market service

Использует существующий `GetCandles` и `ccxt`. Поддерживает Binance и Bybit, UTC timestamps, лимиты и валидацию OHLCV.

### Signal service

Не дублирует индикаторы. Он преобразует существующие `Candle` в DataFrame и вызывает текущий `calculate_features` из ML feature builder. На последней полной строке проверяются `signal_breakout` и `signal_mean_reversion`.

### ML gRPC service

Существующий protobuf и `PredictSignalQuality` не изменяются. Сервис получает свечи и выбранную стратегию, строит признаки и возвращает вероятность, threshold и решение.

### Risk service

Детерминированный слой без ML. Рассчитывает long stop-loss, take-profit и размер позиции. Не исполняет сделки.

### Storage

SQLite хранит итоговые решения. Используется отдельное соединение на операцию и Docker volume.

## Поток данных

```text
GET /api/v1/trading/decision
  -> GetCandles
  -> detect_trading_signal
  -> no_signal: сохранить и вернуть
  -> signal: PredictSignalQuality по gRPC
  -> calculate_risk_parameters
  -> сохранить SQLite
  -> вернуть JSON
```

Если активны обе стратегии, ML вызывается дважды, после чего выбирается стратегия с наибольшим `prob_good_trade`.

## Совместимость

Существующие endpoints `/market/candles`, `/ml/prediction-quality` и protobuf-контракт сохраняются. Новая функциональность подключена отдельными сервисами и router.

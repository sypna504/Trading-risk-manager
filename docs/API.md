# API

## GET /api/v1/health

Возвращает состояние backend, доступность gRPC, model version и UTC-время.

## GET /api/v1/market/candles

Параметры: `exchange`, `symbol`, `interval`, `limit`.

## GET /api/v1/ml/prediction-quality

Существующий endpoint ручной оценки стратегии. Параметр `strategy_name` сохраняется.

## GET /api/v1/ml/model-info

Возвращает config модели, количество признаков, наличие файлов, возраст модели и флаг устаревания.

## GET /api/v1/trading/decision

Параметры:

- `exchange=binance|bybit`;
- `symbol=BTCUSDT`;
- `interval=1m|5m|15m|1h|4h|1d`;
- `limit=60..5000`;
- `account_balance>0`;
- `risk_per_trade_pct=0..10`;
- `max_position_share_pct=1..100`.

### no_signal

Модель не вызывается. Ответ содержит `status=no_signal`, `trade_allowed=false` и причину.

### evaluated

Содержит выбранную стратегию, ML-оценку и `risk_parameters`.

## GET /api/v1/trading/decisions

Фильтры: `limit`, `offset`, `symbol`, `strategy`, `trade_allowed`.

## GET /api/v1/trading/decisions/{decision_id}

Возвращает одну сохранённую запись или `404`.

# Trading Risk Manager

Демонстрационная рекомендательная система для оценки криптовалютных торговых сигналов и расчёта параметров риска.

Система получает свечи Binance или Bybit, автоматически проверяет сигналы `breakout` и `mean_reversion`, передаёт активный сигнал в CatBoost через gRPC, рассчитывает размер позиции, stop-loss и take-profit, а затем сохраняет решение в SQLite.

> Проект не исполняет реальные сделки, не использует API-ключи биржи и не является финансовой рекомендацией.

## Что входит в MVP

- FastAPI backend;
- получение OHLCV через `ccxt`;
- автоматическое определение сигнала;
- Python gRPC ML-сервис;
- CatBoost inference;
- deterministic risk engine;
- история решений в SQLite;
- информация о версии и возрасте модели;
- безопасный pipeline обновления и переобучения;
- минимальный HTML/CSS/JS интерфейс;
- Docker Compose;
- smoke-тесты.

## Архитектура

```text
Browser
   |
   | HTTP
   v
FastAPI backend
   |-- market service -> Binance / Bybit
   |-- signal service -> feature builder
   |-- risk service
   |-- SQLite history
   |
   | gRPC
   v
ML service -> CatBoost model
```

Подробности: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Быстрый запуск через Docker

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

Windows CMD:

```cmd
copy .env.example .env
docker compose build
docker compose up -d
```

После запуска:

- интерфейс: `http://127.0.0.1:8000/`;
- Swagger: `http://127.0.0.1:8000/docs`;
- health: `http://127.0.0.1:8000/api/v1/health`.

## Основные endpoints

### Свечи

```text
GET /api/v1/market/candles
```

### Ручная оценка конкретной стратегии

Существующий endpoint сохранён:

```text
GET /api/v1/ml/prediction-quality
```

### Автоматическое торговое решение

```text
GET /api/v1/trading/decision
```

Параметры:

- `exchange`;
- `symbol`;
- `interval`;
- `limit`;
- `account_balance`;
- `risk_per_trade_pct`;
- `max_position_share_pct`.

Пример:

```text
/api/v1/trading/decision?exchange=binance&symbol=BTCUSDT&interval=1h&limit=100&account_balance=1000&risk_per_trade_pct=1&max_position_share_pct=25
```

### История

```text
GET /api/v1/trading/decisions
GET /api/v1/trading/decisions/{decision_id}
```

### Модель

```text
GET /api/v1/ml/model-info
```

Полное API: [docs/API.md](docs/API.md).

## Risk engine

Для разрешённого long-сигнала система рассчитывает:

- допустимую денежную сумму риска;
- ATR-based stop-loss;
- take-profit с risk/reward не ниже `1:2`;
- размер позиции;
- ограничение позиции максимальной долей баланса.

При `trade_allowed=false` или при отсутствии сигнала размер позиции равен нулю.

## SQLite

По умолчанию база находится в контейнере по пути:

```text
/app/data/trading_risk.db
```

Docker volume `backend_data` сохраняет историю после пересоздания контейнера.

## Обновление данных и переобучение

Windows:

```cmd
scripts\retrain_model.cmd
```

Linux/macOS:

```bash
./scripts/retrain_model.sh
```

Pipeline:

```text
update history
-> build dataset
-> backup current model
-> train candidate
-> evaluate on untouched test
-> promote or restore previous model
-> save JSON report
```

Версия модели формируется как день и месяц:

```text
risk_model_0208
```

После обновления model-файлов ML-сервис нужно пересобрать или перезапустить:

```bash
docker compose up -d --build --force-recreate ml_service
```

Подробнее: [docs/ML_PIPELINE.md](docs/ML_PIPELINE.md).

## Запуск без Docker

Установите зависимости backend и ML-сервиса, а также сгенерируйте protobuf-классы согласно текущей структуре проекта.

Backend:

```bash
uvicorn app.backend.api.app.main:app --host 0.0.0.0 --port 8000
```

ML service:

```bash
python -m app.ml_services.app.online.server
```

Для локального запуска задайте:

```text
ML_SERVICE_ADDRESS=127.0.0.1:50051
DATABASE_PATH=./data/trading_risk.db
MODEL_PATH=app/ml_services/app/models/risk_model_v2_online.cbm
MODEL_CONFIG_PATH=app/ml_services/app/models/risk_model_v2_online_config.json
```

## Тесты

```bash
python -m pip install -r requirements-test.txt
pytest
```

В тестах внешние запросы к биржам подменяются.

## Структура добавленной функциональности

```text
app/backend/api/app/
├── routers/trade_decision_router.py
├── services/signal_service.py
├── services/risk_service.py
├── storage/
├── static/
├── logging_config.py
└── middleware.py

app/ml_services/app/training/
├── update_history.py
├── evaluate_model.py
└── retrain_pipeline.py
```

## Ограничения MVP

- поддерживаются только long-сценарии;
- нет реального исполнения ордеров;
- нет плеча;
- нет авторизации и нескольких пользователей;
- качество решения ограничено качеством текущей модели и обучающих данных;
- простой SQLite рассчитан на локальное MVP-использование.

Подробнее: [docs/MVP_LIMITATIONS.md](docs/MVP_LIMITATIONS.md).

## Следующие шаги

- paper trading;
- мониторинг drift и качества модели;
- раздельные модели по режимам рынка;
- portfolio-level ограничения;
- PostgreSQL для многопользовательской версии;
- CI/CD и расширенное тестирование.

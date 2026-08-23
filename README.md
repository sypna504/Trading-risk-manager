# Trading Risk Manager

Демонстрационная система оценки криптовалютных торговых сигналов и расчёта параметров риска.

Система получает OHLCV Binance или Bybit, определяет `breakout` и `mean_reversion`, передаёт сигнал в CatBoost через gRPC, рассчитывает риск и сохраняет решение в SQLite.

> Проект не исполняет реальные сделки и не является финансовой рекомендацией.

## ML contract v3

Новая production schema устраняет применение одной `1h`-модели к несовместимым таймфреймам.

Для безопасного MVP:

```text
supported_intervals = ["1h"]
target_horizon_minutes = 180
feature_schema_version = "v3"
```

`interval` входит в CatBoost features как категориальный признак, а модель дополнительно использует interval-aware признаки:

- `ret_1h`, `ret_3h`, `ret_12h`, `ret_24h`;
- return и volatility, нормализованные по времени;
- trend и volatility regimes;
- EMA distances и slope;
- Bollinger position;
- downside volatility;
- volume trend;
- rolling drawdown.

Запросы `1m`, `5m`, `15m`, `4h` и `1d` отклоняются, пока для них не обучены отдельные совместимые bundles.

## Вероятности

API возвращает:

```json
{
  "prob_good_trade": 0.42,
  "raw_prob_good_trade": 0.47,
  "calibration_method": "platt",
  "probability_bin": "40-50%",
  "model_supported_interval": "1h"
}
```

Calibration выбирается только на validation между:

- без calibration;
- Platt scaling;
- isotonic regression.

Калибратор отклоняется, если он слишком сильно сжимает распределение probabilities.

## Promotion gate

Модель не становится active при отрицательном trading result, слабом probability spread, низком profit factor, нестабильном walk-forward или отсутствии sensitivity.

Даже прямой вызов `ModelRegistry.promote()` требует валидный:

```text
promotion_decision.json
```

## Docker

```powershell
docker compose build --no-cache ml_service backend ml_trainer
docker compose up -d ml_service backend
```

Swagger:

```text
http://localhost:8000/docs
```

## Тесты

`.venv` не требуется:

```powershell
scripts\run_ml_tests.cmd
```

## Обучение

Сначала candidate-only:

```powershell
scripts\retrain_v3_candidate_only.cmd
```

Затем обучение с возможной автоматической публикацией:

```powershell
scripts\retrain_v3.cmd
```

Candidate публикуется только при прохождении promotion gates.

## Проверка active-модели

```powershell
scripts\model_status.cmd
scripts\check_sensitivity.cmd
```

## Rollback

```powershell
scripts\rollback_model.cmd
```

## Основные endpoints

```text
GET /api/v1/market/candles
GET /api/v1/ml/prediction-quality
GET /api/v1/ml/model-info
GET /api/v1/trading/decision
GET /api/v1/trading/decisions
```

## Важное ограничение

Код pipeline прошёл synthetic-тесты, но новый model artifact не включён. Качество v3 должно быть подтверждено локальным обучением на `history_data.parquet`, независимым test и walk-forward отчётом.

Подробности:

- [APPLY.md](APPLY.md)
- [MODEL_AUDIT.md](MODEL_AUDIT.md)
- [LEAKAGE_AUDIT.md](LEAKAGE_AUDIT.md)
- [PROMOTION_VALIDATION.md](PROMOTION_VALIDATION.md)
- [TEST_REPORT.md](TEST_REPORT.md)

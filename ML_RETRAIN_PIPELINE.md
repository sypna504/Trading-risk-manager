# ML retrain and deployment pipeline

Этот архив расширяет текущую ветку `dev` и не меняет FastAPI, gRPC/protobuf, CatBoost, market endpoints или формат gRPC-запроса.

## Что добавлено

- обновление `history_data.parquet` страницами через CCXT;
- фильтрация незакрытой свечи;
- проверки OHLCV, дублей, неизвестных symbols и временных разрывов;
- rolling training window;
- единый `features_builder.py` для train и inference;
- глобальное разбиение по timestamp с purge;
- CatBoost search из трех небольших конфигураций;
- sanity baselines: constant и logistic regression;
- опциональная Platt/isotonic calibration;
- threshold selection только на validation;
- независимая test-оценка и walk-forward report;
- candidate/champion registry, promotion gates и rollback;
- атомарные записи parquet, JSON и active registry;
- hot reload модели в inference без пересборки Docker image;
- единый retrain orchestrator с lock и guards;
- общие Docker volumes для моделей и данных;
- минимальные unit-тесты критичного пути.

## Как применить архив

Распакуйте архив в корень репозитория `Trading-risk-manager` с заменой существующих файлов. Структура архива уже совпадает со структурой репозитория.

После распаковки установите обновленные зависимости:

```bash
pip install -r app/ml_services/requirements.txt
```

## Официальный ручной запуск на Windows

Из корня репозитория:

```bat
scripts\retrain_and_deploy.cmd manual
```

Принудительный запуск без guards:

```bat
set FORCE_RETRAIN=true
scripts\retrain_and_deploy.cmd manual
```

Прямая Python-команда:

```bat
set PYTHONPATH=%CD%\app\ml_services
python -m app.training.retrain_pipeline --mode manual
```

## Docker-запуск одной командой

```bash
docker compose run --rm ml_trainer
```

Если candidate проходит promotion gates, `registry.json` обновляется атомарно. Запущенный `ml_service` проверяет registry перед prediction и безопасно выполняет hot reload. Пересборка image не требуется.

## Проверка активной модели

Windows:

```bat
scripts\model_status.cmd
```

Python:

```bash
python -m app.training.retrain_pipeline --status
```

## Rollback

Windows:

```bat
scripts\rollback_model.cmd
```

Python:

```bash
python -m app.training.retrain_pipeline --rollback
```

После rollback следующий inference-запрос вызовет hot reload предыдущей модели.

## Ежедневное расписание Windows

В Task Scheduler создайте задачу:

- Program: `C:\Windows\System32\cmd.exe`
- Arguments: `/c C:\path\Trading-risk-manager\scripts\retrain_and_deploy.cmd daily`
- Start in: `C:\path\Trading-risk-manager`
- Trigger: ежедневно, например в `00:10`.

## Будущее почасовое расписание

Запускайте не ровно в `HH:00`, а, например, в `HH:07`:

```bat
scripts\retrain_and_deploy.cmd hourly
```

При этом история может обновляться каждый час, но обучение будет пропущено, если:

- нет новых закрытых свечей;
- новых строк меньше `MIN_NEW_CANDLES_FOR_RETRAIN`;
- не прошло `MIN_HOURS_BETWEEN_RETRAINS`;
- уже выполняется другой retrain;
- `FORCE_RETRAIN` не включен.

## Основные environment variables

| Variable | Default | Назначение |
|---|---:|---|
| `ML_EXCHANGE` | `binance` | `binance` или `bybit` |
| `ML_SYMBOLS` | liquid universe | symbols через запятую |
| `ML_INTERVAL` | `1h` | таймфрейм |
| `TRAINING_WINDOW_DAYS` | `180` | rolling training window |
| `ML_TRAINING_WINDOW_CANDIDATES` | `90,180,365` | окна для optional pre-test comparison |
| `ML_AUTO_SELECT_TRAINING_WINDOW` | `false` | включить выбор окна по pre-test walk-forward |
| `ML_TARGET_HORIZON` | `3` | горизонт target в свечах |
| `ML_FEE` | `0.001` | комиссия на одну сторону |
| `ML_SLIPPAGE` | `0.0005` | slippage на одну сторону |
| `ML_REQUEST_LIMIT` | `1000` | размер страницы API |
| `ML_REQUEST_TIMEOUT` | `20` | timeout в секундах |
| `ML_MINIMUM_HISTORY_ROWS` | `500` | минимум свечей на symbol |
| `ML_HISTORY_SYMBOL_POLICY` | `extend` | `extend`, `error` или `filter` для symbols, уже находящихся в parquet |
| `ML_MINIMUM_DATASET_ROWS` | `1000` | минимум ML-строк |
| `ML_MINIMUM_CLASS_ROWS` | `100` | минимум каждого класса |
| `ML_MINIMUM_SELECTED_TRADES` | `50` | минимум сделок выше threshold |
| `ML_MAXIMUM_ALLOWED_DRAWDOWN` | `-0.35` | gate по drawdown |
| `MIN_NEW_CANDLES_FOR_RETRAIN` | `24` | guard новых строк |
| `MIN_HOURS_BETWEEN_RETRAINS` | `20` | guard частоты обучения |
| `FORCE_RETRAIN` | `false` | игнорировать guards |
| `RETRAIN_ON_DATA_CHANGE_ONLY` | `true` | учиться только при изменении данных |
| `ML_ENABLE_CALIBRATION` | `true` | проверять calibration |
| `ML_CALIBRATION_METHOD` | `platt` | `platt` или `isotonic` |
| `ML_DEPLOY_AFTER_TRAINING` | `true` | разрешить promotion |
| `ML_RESTART_SERVICE_AFTER_PROMOTION` | `false` | restart вместо hot reload |
| `ML_INFERENCE_VERSION_URL` | пусто | optional HTTP endpoint проверки версии |
| `ML_MODELS_ROOT` | `app/ml_services/app/models` | общий model volume |
| `ML_HISTORY_PATH` | training data path | history parquet |
| `ML_DATASET_PATH` | training data path | ML dataset parquet |

## Promotion strategy

Candidate продвигается, только если:

- test содержит оба класса;
- ROC AUC > 0.5;
- PR AUC выше positive-class baseline;
- probabilities не константные;
- достаточно уникальных probabilities и выбранных сделок;
- mean и total net return положительные;
- maximum drawdown не превышает лимит;
- результат не сконцентрирован в одной монете или стратегии;
- candidate не хуже champion на том же test-периоде;
- calibration не ухудшилась существенно.

Если gate провален, active-модель не меняется. Candidate и причины rejection остаются в registry/report.

## Тесты

Из `app/ml_services`:

```bash
pytest app/training/tests -q
```

В unit-тестах биржевые запросы не выполняются.

## Ограничения

1. В архив не включены новые обученные веса: качество нельзя честно заявлять без запуска на ваших актуальных parquet.
2. CCXT universe должен соответствовать реальным spot markets выбранной биржи.
3. `total_net_return` пока агрегирует независимые candidate trades и не моделирует капитал, одновременные позиции и лимиты экспозиции как полноценный portfolio backtester.
4. Hot reload происходит перед prediction. Текущий запрос использует целиком старую или целиком новую модель, но не смешивает их.
5. `ML_INFERENCE_VERSION_URL` опционален, потому что текущий публичный FastAPI endpoint версии не был доступен в аудируемых файлах. gRPC response уже содержит `model_version`.
6. Отдельные thresholds по стратегиям намеренно не включены до доказательства на walk-forward.
7. Полное переобучение на rolling window используется по умолчанию; `init_model` не применяется без независимого сравнения.


## Ошибка `unknown symbols found`

Причина ошибки: symbols уже находились в `history_data.parquet`, но отсутствовали в `TrainingConfig.symbols`. Строгая валидация считала их неизвестными и останавливала pipeline до обучения.

В исправленной версии:

- default universe дополнен symbols из существующего parquet;
- добавлен параметр `ML_HISTORY_SYMBOL_POLICY`;
- значение по умолчанию `extend` сохраняет существующую историю и разрешает найденные в ней symbols;
- `error` оставляет старое строгое поведение;
- `filter` удаляет из сохраняемой истории symbols, отсутствующие в конфигурации.

Для текущего проекта рекомендуется:

```text
ML_HISTORY_SYMBOL_POLICY=extend
```

После замены файлов снова запусти:

```bat
scripts\retrain_and_deploy.cmd manual
```

Проверка тестов:

```bat
scripts\run_ml_tests.cmd
```

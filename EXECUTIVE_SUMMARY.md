# Executive summary

## Scope

Аудит выполнен для ветки `feature/auto-signal-choseing` по предоставленному техническому заданию. Проверялись критические пути FastAPI, автоматического выбора сигнала, gRPC-валидации, CatBoost inference, model metadata, risk engine, SQLite и deployment-конфигурации.

## Итог

Проект имеет развитую MVP-архитектуру, но до проверки содержал несколько ошибок, способных давать неверные торговые решения или ломать запуск в чистом окружении.

Найдено и исправлено:

- blocker: 1;
- critical: 4;
- major: 6;
- minor: 2.

Ключевые исправления:

- исключены незакрытые свечи из online inference;
- запрещён молчаливый откат к старой строке признаков;
- backend теперь читает активную модель из registry;
- исправлена переносимость и согласованность model metadata;
- усилена gRPC-валидация NaN, inf и OHLC;
- исправлен hot reload legacy-модели, который мог происходить на каждом запросе;
- risk engine защищён от нечисловых значений и отрицательного stop-loss;
- multi-strategy flow стал устойчив к частичному отказу одной стратегии;
- SQLite-соединения гарантированно закрываются, включены WAL и busy timeout;
- согласованы версии `grpcio`, `grpcio-tools` и `protobuf` с checked-in generated code;
- добавлен persistent volume SQLite и read-only model volume для backend.

## Фактически выполненные проверки

- `python -m compileall -q app tests ml` — успешно;
- smoke + audit regression tests — **28 passed**;
- те же тесты с `ResourceWarning` как ошибкой — **28 passed**;
- диагностическое покрытие выбранных критических модулей — **65% total**;
- FastAPI через `TestClient`: `/`, `/docs`, `/openapi.json`, static assets — HTTP 200;
- OpenAPI содержит все ожидаемые MVP endpoints;
- `docker-compose.yml` успешно разобран как YAML, проверены сервисы, зависимости и volumes.

## Что не было выполнено в текущем окружении

- реальная сборка и запуск Docker: команда `docker` недоступна;
- live-запросы Binance/Bybit: намеренно не выполнялись;
- полный CatBoost retrain/promotion/rollback с реальными parquet и бинарными моделями: не выполнялся, поскольку в локальном runtime не было полного clone ветки, Docker и `pyarrow`.

Следовательно, статус: **кодовый MVP существенно укреплён и локальные критические проверки проходят, но перед merge обязательна Docker- и full-pipeline-валидация на машине пользователя**.

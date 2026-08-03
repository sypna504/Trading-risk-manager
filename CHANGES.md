# Состав изменений

## Добавлено

- воспроизводимые backend и ML settings;
- `.env.example`;
- расширенный Docker Compose с volume и healthchecks;
- автоматический signal service;
- единый trading decision endpoint;
- risk engine;
- SQLite history и history endpoints;
- model-info endpoint;
- безопасное обновление history и retraining pipeline;
- model version `ddMM`;
- минимальный web-интерфейс;
- logging и request ID;
- документация;
- smoke-тесты.

## Минимально изменено

- `main.py` для lifespan, router и static;
- `grpc_client.py` для timeout, readiness и закрытия channel;
- market service и router для timeout, UTC и корректных ошибок;
- ML router для model-info и сохранения старого endpoint;
- `train_model.py` для версии модели и проверок данных;
- requirements, `.gitignore`, `.dockerignore`, Docker Compose.

## Не изменено

- protobuf-контракт;
- существующий gRPC RPC;
- CatBoost feature builder;
- формула target;
- текущие имена model-файлов;
- существующие API paths.

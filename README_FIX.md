# Исправление путей модели в Docker

Проблема возникала потому, что `registry.json` создавался на Windows и сохранял пути с `\`:

```text
active\risk_model_v2_online\model.cbm
```

Linux-контейнер воспринимал обратный слеш как обычный символ и искал несуществующий файл.

## Что исправлено

- `ModelPredictor` читает пути как с `/`, так и с `\`.
- Небезопасные абсолютные пути и `..` блокируются.
- `ModelRegistry` всегда сохраняет пути в POSIX-формате с `/`.
- Старый `registry.json` автоматически нормализуется при запуске training-кода.
- Добавлен отдельный скрипт для однократного исправления текущего registry.
- `ml_trainer` вынесен в Docker profile `training` и больше не запускается через обычный `docker compose up`.
- Backend ждёт healthy-состояния ML-сервиса.
- Добавлены тесты Windows/Linux-путей, promotion и rollback.

## Установка

Скопируй содержимое архива в корень проекта с заменой файлов.

Не удаляй каталоги `models/active`, `models/candidates`, `models/archive` и файл модели.

## Исправление текущего registry

Из корня проекта:

```powershell
scripts\fix_registry_paths.cmd
```

Скрипт создаст резервную копию:

```text
app/ml_services/app/models/registry.json.bak
```

## Пересборка и запуск

```powershell
docker compose down
docker compose build --no-cache ml_service backend ml_trainer
docker compose up -d ml_service backend
docker compose ps
docker compose logs --tail 100 ml_service
```

Обычный `docker compose up -d` теперь тоже не запускает trainer.

## Проверка health

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

Ожидается:

```text
status      : ok
backend     : available
ml_service  : available
```

## Запуск обучения

```powershell
docker compose --profile training run --rm ml_trainer
```

После promotion ML-сервис читает новую active-модель из общего volume.

## Тесты

```powershell
scripts\run_ml_tests.cmd
```

Новые тесты проверяют:

- чтение старых Windows-путей внутри Linux;
- блокировку path traversal;
- сохранение POSIX-путей при bootstrap, promotion и rollback;
- исправление старого registry.

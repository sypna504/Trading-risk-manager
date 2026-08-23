# Runtime compatibility fix v5

Исправлены две ошибки, обнаруженные после установки v4.

## 1. Ошибка trading decision

Было:

```text
TypeError: latest_complete_feature_row() takes 1 positional argument but 2 were given
```

Причина: backend продолжал передавать отдельный список обязательных колонок, а v3 feature builder оставил только одноаргументную сигнатуру.

Исправление:

```python
latest_complete_feature_row(features_df, required_columns=None)
```

Старый backend contract снова поддерживается.

## 2. Ошибка prediction-quality 502

Одновременно были возможны три несовместимости:

- active champion остаётся legacy v2 и ожидает `hour`/`weekday`, а v3 inference возвращал только v3 columns;
- protobuf-классы могли быть сгенерированы из старого контракта;
- legacy calibrator был сохранён sklearn 1.8.0, но загружался sklearn 1.9.0.

Исправления:

- inference возвращает полную вычисленную строку; predictor сам выбирает schema активной модели;
- Dockerfile генерирует protobuf после копирования проекта и проверяет новые поля;
- sklearn закреплён на версии 1.8.0;
- gRPC client возвращает код и детали ошибки;
- добавлен runtime smoke test.

## Применение

Распаковать архив в корень репозитория с заменой файлов, затем:

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFY_AND_REBUILD.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\runtime_smoke_test.ps1
```

## Ожидаемый результат

`prediction-quality` должен вернуть HTTP 200 и поля:

```text
prob_good_trade
raw_prob_good_trade
calibration_method
probability_bin
model_supported_interval
```

`trading/decision` должен вернуть HTTP 200, даже если итоговый статус `no_signal` или `trade_allowed=false`.

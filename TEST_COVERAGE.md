# ML tests

Добавлены unit-тесты для функций и критичных веток следующих модулей:

- `features_builder.py`;
- `training_config.py`;
- `data_validation.py`;
- `update_history.py`;
- `build_dataset.py`;
- `time_split.py`;
- `evaluate_model.py`;
- `drift_report.py`;
- `train_model.py`;
- `window_selection.py`;
- `model_registry.py`;
- `pipeline_lock.py`;
- `retrain_pipeline.py`;
- `online/model_predictor.py`;
- `online/server.py`;
- `config.py`.

Проверяются в том числе:

- нормализация symbols и timestamp;
- все три политики неизвестных symbols: `extend`, `error`, `filter`;
- отсутствие дублей после merge;
- исключение незакрытой свечи;
- пагинация биржевых свечей;
- атомарная запись JSON и parquet;
- OHLCV-инварианты;
- rolling window;
- временные split и purge;
- threshold selection;
- calibration;
- classification/trading metrics;
- candidate promotion и rollback;
- hot reload модели;
- guards и lock retrain pipeline;
- успешный, пропущенный и аварийный запуск pipeline.

Локальный результат проверки патча:

```text
97 passed
95% statement coverage
```

Запуск на Windows:

```bat
scripts\run_ml_tests.cmd
```

Запуск напрямую:

```bash
python -m pytest app/ml_services/app/training/tests -q
```

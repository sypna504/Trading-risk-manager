# Validation results

Проверки, выполненные при подготовке архива:

- `python -m compileall` для всех Python-файлов: успешно;
- YAML-разбор `docker-compose.yml`: успешно;
- unit-тесты критичного пути: `9 passed`;
- synthetic CatBoost candidate-training smoke test: успешно;
- candidate artifacts (`model.cbm`, config, metrics): созданы;
- hot reload test после изменения registry: успешно.

Unit-тесты покрывают:

- идемпотентное объединение истории;
- обновление дублирующейся свечи свежей копией;
- исключение незакрытой свечи;
- обнаружение дублей;
- глобальный timestamp split без пересечений;
- движение rolling window;
- rejection promotion gate;
- promotion и rollback;
- lock от двух одновременных jobs;
- hot reload `model_version` после promotion.

Не выполнялось:

- обучение на фактическом `history_data.parquet` пользователя;
- реальные Binance/Bybit запросы;
- фактическое сравнение candidate/champion;
- подтверждение улучшения финансовых метрик.

Поэтому архив не заявляет улучшение модели до локального запуска на независимом test и walk-forward.


## Patch v2

- исправлена ошибка `unknown symbols found`;
- добавлены policies `extend/error/filter`;
- default universe синхронизирован с symbols из пользовательского parquet;
- unit tests: `97 passed`;
- statement coverage: `95%`;
- Python compileall: успешно.

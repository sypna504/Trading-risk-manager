# Experiment results

## Реально выполнено в этой среде

- синтаксическая проверка Python-файлов;
- 103 unit/integration/model tests;
- synthetic CatBoost candidate training через тестовый набор;
- проверка interval contract;
- проверка physical purge;
- проверка блокировки negative candidate;
- проверка обязательного promotion decision artifact;
- проверка sensitivity report.

## Не выполнялось

- обучение на пользовательском `history_data.parquet`;
- live Binance/Bybit calls;
- Docker build, поскольку Docker недоступен в среде сборки;
- реальный walk-forward на полной рыночной истории;
- сравнение v3 с active champion на пользовательских данных.

## Вывод

Код устраняет обнаруженные contract и MLOps ошибки, но качество новой модели должно быть подтверждено локальным retrain. До этого статус v3: `implementation_ready, model_quality_not_yet_verified`.

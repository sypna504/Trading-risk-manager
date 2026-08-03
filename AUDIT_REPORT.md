# Аудит ML-контура ветки `dev`

## Уже сделано правильно

- Train и inference используют единый `features_builder.py`.
- Rolling-признаки считаются отдельно внутри symbol.
- Уровни `high_20`, `high_50`, `low_50` сдвинуты на одну свечу.
- Entry рассчитывается на следующем open, outcome — на будущих свечах.
- CatBoost использует отдельный validation для early stopping.
- gRPC response уже содержит probability, risk score, threshold, decision и model version.

## Критичные проблемы исходной версии

1. Train/validation/test делились по строкам, а не по глобальным timestamp.
2. Не было purge между временными частями при target horizon > 0.
3. Test создавался, но не использовался для независимой полной оценки.
4. Threshold выбирался только по validation total return.
5. Новая модель сохранялась поверх текущей без candidate/champion registry.
6. Не было атомарной публикации, rollback и promotion gates.
7. Модель была привязана к Docker image и не имела безопасного reload.
8. Не было воспроизводимого пагинированного обновления history parquet.
9. Не исключалась незакрытая свеча единым контролируемым модулем.
10. Не было OHLCV validation, gap report, drift report и training report.
11. Не было guards от повторного или слишком частого переобучения.
12. Не было sanity comparison с constant и logistic baselines.
13. Не проверялась calibration вероятностей.

## Возможные data leakage

- один timestamp мог оказаться сразу в разных split через разные symbols;
- target последних train-строк использовал цены из следующей временной части;
- ручной подбор threshold и параметров после просмотра test;
- walk-forward без независимого test-блока внутри fold;
- публикация модели без сравнения candidate/champion на одинаковом test.

## Что изменено в архиве

- глобальный timestamp split и purge;
- независимый test;
- walk-forward train/validation/test folds;
- rolling window;
- threshold selection только на validation;
- optional calibration;
- comprehensive evaluation;
- paginated history update и atomic parquet replacement;
- candidate/champion registry, gates, rollback;
- shared model/data Docker volumes;
- thread-safe inference hot reload;
- retrain pipeline с lock, guards и reports.

## Что нельзя подтвердить без локальных данных

- фактическое улучшение модели;
- реальный ROC AUC, PR AUC, Brier score и trading metrics;
- оптимальное rolling window;
- оптимальную cadence daily/hourly/weekly;
- отсутствие проблем внутри фактического `history_data.parquet`.

Эти выводы должны быть получены только после запуска архива на актуальных данных и независимом test/walk-forward.

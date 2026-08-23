# Аудит и выполненные исправления

## Корневые причины одинаковых вероятностей

1. `interval` присутствовал в gRPC request, но отсутствовал в feature schema и CatBoost Pool.
2. Production-модель обучалась только на `1h`, однако API разрешал `1m`, `5m`, `15m`, `4h` и `1d`.
3. `symbol` и `strategy_name` имели нулевую importance у текущей active-модели.
4. CatBoost остановился на 16 деревьях и почти полностью использовал `hour`, `weekday` и `atr_14_pct`.
5. Platt calibration сжал probabilities до узкого диапазона.
6. Модель с отрицательными trading metrics была записана в active registry.

## Что изменено

- новая feature schema `v3`;
- `interval` добавлен в `FEATURE_COLUMNS` и `CAT_FEATURES`;
- безопасный MVP ограничен моделью `1h`;
- target horizon задан физически: 180 минут;
- добавлены interval-aware признаки `ret_1h`, `ret_3h`, `ret_12h`, `ret_24h`;
- добавлены trend, volatility, volume и regime признаки;
- `hour` и `weekday` удалены из production feature schema;
- target хранит entry/exit convention, fee, slippage, MFE и drawdown;
- split использует физический purge/embargo, а не число signal timestamps;
- calibration выбирается между none, Platt и isotonic только по validation;
- raw и calibrated probabilities сохраняются отдельно;
- thresholds выбираются отдельно по стратегиям при достаточном числе строк;
- добавлен controlled sensitivity report;
- promotion gate проверяет probability spread, profit factor, walk-forward и trading metrics;
- `promote()` требует `promotion_decision.json`, поэтому прямой вызов больше не обходит gate;
- legacy v2 временно разрешён только для `1h`, пока v3 candidate не прошла promotion;
- API возвращает raw probability и сведения о calibration.

## Ограничения

Архив не содержит нового обученного model artifact. Новую модель нужно обучить на локальном `history_data.parquet`. Нельзя утверждать, что v3 лучше active-модели до получения независимых test и walk-forward результатов.

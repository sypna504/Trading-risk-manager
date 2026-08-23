# Leakage audit

## Исправлено

- train, validation и test разделяются глобально по timestamp;
- purge gap задаётся в физическом времени;
- purge включает target horizon и embargo;
- один timestamp не может находиться в разных splits;
- calibration и threshold selection используют разные части validation;
- test не используется для calibration или threshold selection;
- walk-forward использует отдельные model-selection и threshold блоки;
- target строится только через будущие свечи внутри одного `symbol + interval`.

## Сохраняющиеся риски

- многократное promotion-сравнение на перекрывающихся test-периодах может привести к adaptive overfitting;
- правила signal generation являются частью dataset selection и могут создавать selection bias;
- exchange data quality и пропуски свечей требуют отдельного мониторинга;
- paper-trading outcome должен оставаться независимым от обучения до следующего retrain.

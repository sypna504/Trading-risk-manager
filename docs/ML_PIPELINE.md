# ML pipeline

## Текущие артефакты

```text
history_data.parquet
  -> build_dataset.py
  -> ml_dataset_v2.parquet
  -> train_model.py
  -> risk_model_v2_online.cbm
  -> risk_model_v2_online_config.json
```

## Автоматический pipeline

`retrain_pipeline.py` выполняет:

1. `update_history()`;
2. существующий `build_dataset()`;
3. резервное копирование active model и config;
4. существующий `train_model()`;
5. оценку candidate на последних 15% данных;
6. сравнение с предыдущей моделью;
7. promotion или rollback;
8. JSON-отчёт.

## Метрики

- ROC AUC;
- PR AUC;
- precision;
- recall;
- F1;
- количество и доля выбранных сделок;
- win rate;
- mean и total net return;
- maximum drawdown простой equity curve;
- статистика вероятностей;
- количество уникальных вероятностей;
- количество деревьев.

## Promotion gate

Candidate отклоняется, если:

- test содержит один класс;
- ROC AUC не выше `0.5`;
- недостаточно выбранных сделок;
- mean или total return неположительные;
- вероятности постоянны;
- candidate хуже предыдущей модели по ключевым метрикам.

## Версия

`MODEL_VERSION` задаётся окружением. При отсутствии значения используется UTC-дата `ddMM`.

Пример:

```text
risk_model_0208
```

Имя рабочего файла остаётся постоянным, поэтому существующий inference не нужно переделывать.

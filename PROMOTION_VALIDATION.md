# Promotion validation

Candidate не публикуется, если выполняется хотя бы одно условие:

- test содержит один класс;
- ROC AUC не выше 0.5;
- PR AUC не выше positive class rate;
- probability unique count ниже лимита;
- probability std или range слишком малы;
- выбрано слишком мало сделок;
- mean return или total return не положительны;
- profit factor не выше 1;
- drawdown превышает лимит;
- недостаточно walk-forward folds;
- доля положительных walk-forward folds ниже лимита;
- результат сосредоточен на одном symbol или strategy;
- sensitivity показывает константную модель;
- candidate хуже champion по return, drawdown или Brier сверх допуска.

После gate создаётся:

```text
candidates/<version>/promotion_decision.json
```

`ModelRegistry.promote()` без этого файла завершается ошибкой. Это закрывает старый путь прямой публикации плохой candidate.

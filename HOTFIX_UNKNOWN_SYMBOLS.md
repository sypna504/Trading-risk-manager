# Hotfix: unknown symbols

Ошибка возникала потому, что `history_data.parquet` содержал symbols, которых не было в `TrainingConfig.symbols`.

Исправления:

1. `DEFAULT_SYMBOLS` дополнен symbols из существующей истории.
2. Добавлен `ML_HISTORY_SYMBOL_POLICY`:
   - `extend` — сохранить и обновлять symbols из parquet, даже если их нет в `ML_SYMBOLS`;
   - `error` — остановиться при неизвестном symbol;
   - `filter` — удалить такие symbols из сохраняемой истории.
3. Default: `extend`.
4. В history report теперь есть:
   - `configured_symbols`;
   - `fetch_symbols`;
   - `history_only_symbols`;
   - `history_symbol_policy`;
   - `failed_symbols`.

Рекомендуемый запуск:

```bat
set ML_HISTORY_SYMBOL_POLICY=extend
scripts\retrain_and_deploy.cmd manual
```

Проверка тестов:

```bat
scripts\run_ml_tests.cmd
```

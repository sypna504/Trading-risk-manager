# Файлы патча

Заменить:

- `app/ml_services/app/online/model_predictor.py`
- `app/ml_services/app/training/model_registry.py`
- `app/ml_services/app/training/tests/test_model_predictor_full.py`
- `app/ml_services/app/training/tests/test_model_registry_full.py`
- `docker-compose.yml`

Добавить:

- `scripts/fix_registry_paths.py`
- `scripts/fix_registry_paths.cmd`
- `README_FIX.md`

`app/ml_services/app/models/registry.json` намеренно не входит в патч, чтобы не затереть текущую active-модель. Его исправляет `scripts/fix_registry_paths.cmd`.

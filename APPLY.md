# APPLY

Patch: `research-final-v10`

Base state: `sypna504/Trading-risk-manager`, branch `feature/auto-signal-choseing`.

This archive is an **overlay patch**. Extract its contents directly into the repository root. It intentionally does not ship active model binaries, `registry.json`, real `history_data.parquet`, `ml_dataset_v3.parquet`, or SQLite data.

## 1. Capture and back up the current state

```powershell
git checkout feature/auto-signal-choseing
git rev-parse HEAD
git status
Copy-Item .\app\ml_services\app\models\registry.json .\app\ml_services\app\models\registry.json.before-research-v10 -ErrorAction SilentlyContinue
Copy-Item .\app\ml_services\app\training\data\history_data.parquet .\app\ml_services\app\training\data\history_data.parquet.before-research-v10 -ErrorAction SilentlyContinue
```

## 2. Apply the archive

Extract the ZIP **directly into the repository root** with replacement. There must be no wrapper directory such as `trading_risk_manager_research_final/` around `app/`, `scripts/`, and `docker-compose.yml`.

Remove stale files left by older overlays:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cleanup_stale_reports.ps1
```

## 3. Dependency / static contract checks

Using the existing local Python installation:

```powershell
python scripts\check_dependency_contract.py
python scripts\check_settings_contract.py
python scripts\check_patch_consistency.py
python scripts\check_proto_contract.py
```

Disposable clean dependency install, without creating a project `.venv`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_fresh_install.ps1
```

## 4. Full local test suite

```powershell
python scripts\test_all.py
```

The suite compiles Python files, checks dependencies/settings/patch/protobuf source contracts, then runs regression, ML/training, repository-level and integration tests.

## 5. Docker build + offline runtime validation

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFY_AND_REBUILD.ps1
```

This is the preferred Docker validation command. It rebuilds images and validates active-model loading, protobuf imports, gRPC health/readiness, backend startup and SQLite persistence without requiring a live Binance request.

## 6. Normal runtime

```powershell
docker compose up -d ml_service backend
docker compose ps
```

- UI: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Model info: `http://localhost:8000/api/v1/ml/model-info`

Live Binance smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\runtime_smoke_test.ps1
```

Full diagnostics on any runtime problem:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnose_runtime.ps1
```

## 7. Synthetic research validation

The synthetic command uses a deterministic OHLCV fixture bundled with the patch. It validates the full research control flow but **does not prove trading edge**.

```powershell
scripts\research_synthetic.cmd
```

Equivalent Docker command:

```powershell
docker compose --profile training run --rm `
  ml_trainer `
  python -m app.research.synthetic_runner
```

Results are persisted to:

```text
runtime/synthetic_research/
```

## 8. Full real-data research

This is the primary research command:

```powershell
docker compose --profile training run --rm `
  ml_trainer `
  python -m app.research.runner --mode full --update-history
```

Or:

```powershell
scripts\research_full.cmd
```

The `ml_trainer` service mounts:

```text
./app/ml_services/app/training/data -> /app/app/training/data
./app/ml_services/app/models        -> /app/app/models
./runtime                            -> /app/runtime
```

Therefore the command uses and updates the host file:

```text
app/ml_services/app/training/data/history_data.parquet
```

and persists research outputs to:

```text
runtime/research/
```

The research pipeline freezes all target/feature/architecture/class-weight/hyperparameter/calibration/threshold decisions on development partitions. `final_holdout` is first accessed only after those decisions are frozen. If no robust result passes the absolute economic/robustness gates, `LATEST.json` contains:

```text
research_result = NO ROBUST EDGE FOUND
promotion_ready = false
candidate = null
```

A weak model is never automatically promoted.

## 9. View research results

```powershell
scripts\research_results.cmd
```

Raw artifacts:

```text
runtime/research/LATEST.json
runtime/research/BEST_RESEARCH_CONFIG.json
runtime/research/FINAL_METRICS.json
runtime/research/EXPERIMENT_TABLE.csv
runtime/research/reports/
runtime/research/experiments/
```

## 10. Check research candidate

```powershell
scripts\research_candidate.cmd
```

If `promotion_ready=false`, stop here. Do not force promotion.

## 11. Model status

```powershell
scripts\model_status.cmd
```

## 12. Promote a research candidate only after it passes gates

For a same-schema v3 candidate:

```powershell
scripts\research_promote.cmd MODEL_VERSION
```

If the active model is still legacy v2, explicit schema migration authorization is required:

```powershell
scripts\research_promote.cmd MODEL_VERSION --allow-schema-migration
```

This command reruns the normal promotion gate. `--allow-schema-migration` authorizes only the schema boundary; it does **not** bypass quality gates.

## 13. Existing candidate-only / retrain commands

Standard v3 candidate-only training:

```powershell
scripts\retrain_v3_candidate_only.cmd
```

Existing explicit v2→v3 retrain flow:

```powershell
scripts\retrain_v3_schema_upgrade.cmd
```

Normal same-schema retrain after a v3 model is active:

```powershell
scripts\retrain_v3.cmd
```

## 14. Rollback

```powershell
scripts\rollback_model.cmd
```

## 15. Linux equivalents

```bash
./scripts/research_synthetic.sh
./scripts/research_full.sh
./scripts/research_results.sh
./scripts/research_candidate.sh
./scripts/research_promote.sh MODEL_VERSION --allow-schema-migration
./scripts/model_status.sh
./scripts/rollback_model.sh
./scripts/test_all.sh
./scripts/docker_validate.sh
```

## Safety rule

Never force-promote a rejected candidate. A successful research execution may legitimately end with `NO ROBUST EDGE FOUND`.

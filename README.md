# Trading Risk Manager

Research / paper-trading MVP для криптовалютных сигналов, ML meta-labeling, risk planning, outcome monitoring и leakage-safe quant research.

> Проект не исполняет реальные сделки и не является финансовой рекомендацией.

## Current contract

- Active legacy v2 is supported only as `legacy_experimental` fallback.
- Validated v3 runtime is Binance Spot, `1h`, closed candles only.
- Training/inference share the same production feature contract.
- Default v3 trade semantics: signal closes → next-bar open → ATR/minimum stop → R-multiple TP → first touch TP/SL → timeout → fees/slippage.
- Promotion requires predictive, economic, portfolio, cost-stress and walk-forward evidence. AUC alone is insufficient.

## Frozen research implementation

The research implementation is under:

```text
app/ml_services/app/research/
```

It performs target comparison, feature ablation, architecture/class-weight/CatBoost selection, calibration and threshold selection, walk-forward evaluation, event-driven portfolio backtesting, cost stress, concentration analysis, block bootstrap confidence intervals and final deployable refit only after OOS gates pass.

The final holdout is not used to choose target, features, hyperparameters, calibration or threshold. If the frozen configuration does not demonstrate robust edge, the run completes as:

```text
NO ROBUST EDGE FOUND
```

and no production promotion occurs.

## Quick validation

```powershell
python scripts\test_all.py
powershell -ExecutionPolicy Bypass -File .\VERIFY_AND_REBUILD.ps1
scripts\research_synthetic.cmd
```

## Full real-data research

```powershell
docker compose --profile training run --rm `
  ml_trainer `
  python -m app.research.runner --mode full --update-history
```

The trainer has read/write access to `app/ml_services/app/training/data` and persists research artifacts through `./runtime:/app/runtime`.

View results:

```powershell
scripts\research_results.cmd
scripts\research_candidate.cmd
```

## Promotion

Check current model:

```powershell
scripts\model_status.cmd
```

Promote only a research candidate that already reports `promotion_ready=true`:

```powershell
scripts\research_promote.cmd MODEL_VERSION
```

Legacy v2 → v3 requires explicit schema migration authorization:

```powershell
scripts\research_promote.cmd MODEL_VERSION --allow-schema-migration
```

Rollback:

```powershell
scripts\rollback_model.cmd
```

## Runtime

```powershell
docker compose up -d ml_service backend
```

- UI: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Model info: `http://localhost:8000/api/v1/ml/model-info`

Live Binance runtime smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\runtime_smoke_test.ps1
```

## Reports

Root reports describe the package validation state. A real local research run creates detailed run-specific reports under `runtime/research/reports/` and per-experiment JSON under `runtime/research/experiments/`.

See `APPLY.md` for the complete application, validation, research, promotion and rollback procedure.

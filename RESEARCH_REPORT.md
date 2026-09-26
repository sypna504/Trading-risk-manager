# Research Report

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Frozen implementation status

Research implementation: **PASS** for code, tests and synthetic end-to-end execution.

Synthetic execution:

- experiments: **17**
- result: **NO ROBUST EDGE FOUND**
- promotion ready: **False**
- candidate exported: **NO**
- production trading ready: **false**

## Full real-data contract

```powershell
docker compose --profile training run --rm `
  ml_trainer `
  python -m app.research.runner --mode full --update-history
```

Compose mounts the host training-data directory read/write and `./runtime:/app/runtime`. The run updates/reads the mounted `history_data.parquet` and writes reports/experiments to `runtime/research/` without path edits.

Selection uses development partitions only. `final_holdout` is first consumed after target/features/architecture/class-weight/hyperparameters/calibration/threshold/seed are frozen. If gates fail, the run writes `research_result=NO ROBUST EDGE FOUND`, leaves `promotion_ready=false`, and does not promote a model.

Real Binance dataset research: **NOT RUN**. Real v3 improvement: **NOT PROVEN**.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

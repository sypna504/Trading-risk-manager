# Calibration Report

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Synthetic validation

- calibration: `{"__global__": "none"}`
- threshold(s): `{"__global__": 0.22000000000000003, "breakout": 0.22000000000000003, "mean_reversion": 0.24000000000000002}`
- final synthetic Brier: `0.1351907329559662`

Calibration selection is performed before final holdout evaluation. Real Binance calibration result: **NOT RUN**.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

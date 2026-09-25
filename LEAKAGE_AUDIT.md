# Leakage Audit

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Result

Code/test leakage audit: **PASS** for the implemented split contract.

Confirmed by regression/ML tests:

- chronological splits only;
- physical target-horizon purge + embargo;
- market-context causality test;
- separate model selection, calibration fit, calibration selection, threshold selection and OOS partitions;
- final holdout separated from development decisions;
- target first-touch/gap/cost semantics covered by regression tests;
- deployable refit occurs only after frozen evaluation gates pass.

In `runner.py`, `final_holdout` is first read for final evaluation only after target, feature, architecture, class-weight, hyperparameter and seed choices have been frozen. Real Binance leakage audit metrics remain **NOT RUN** until the full local research command is executed.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

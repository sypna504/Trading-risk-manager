# Walk Forward Report

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Synthetic result

- completed folds: `2`
- positive-return fold rate: `0.0`
- median portfolio return: `-0.07609046595339386`
- worst portfolio return: `-0.08091931907217131`

Synthetic walk-forward completed successfully but did **not** demonstrate edge. Full Binance walk-forward: **NOT RUN**.

Each fold follows train → model selection → calibration fit/selection → threshold selection → untouched OOS fold.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

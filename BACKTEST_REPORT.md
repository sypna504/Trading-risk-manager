# Backtest Report

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Implementation

Event-driven portfolio backtester validation: **PASS** through unit/regression/synthetic execution. It enforces concurrent-position, gross-exposure and portfolio-risk limits and computes an equity curve rather than simply summing trade returns.

## Final synthetic holdout (validation-only)

- trades: `86`
- portfolio return: `-0.1072631964821048`
- profit factor: `0.37457153824274436`
- maximum drawdown: `-0.11021623221574406`
- 1.5x cost return: `-0.13569655074287634`
- 2x cost return: `-0.16325331811060895`

Synthetic economic result failed the research gates. Real Binance backtest: **NOT RUN**.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

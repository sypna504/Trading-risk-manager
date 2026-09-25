# Model Comparison

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Synthetic research-only comparison

The synthetic smoke exercised pooled, separate-strategy, separate-symbol, separate-liquidity and regression research paths. The deployable architecture remained `pooled`.

Final synthetic classifier:

- feature set: `production_full`
- ROC AUC: `0.44750949296403847`
- PR AUC: `0.12081739587268647`
- PR baseline: `0.13261648745519714`
- Brier: `0.1351907329559662`

These numbers are **not** a model-quality claim. Real comparison against the active legacy model and a real Binance v3 candidate: **NOT RUN**.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

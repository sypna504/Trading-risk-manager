# Target Audit

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Contract

Research target selection is performed on development partitions only. The synthetic smoke selected `ft_atr100_r10_3h` only as a synthetic validation result; it is **not** evidence that this target is best on Binance data.

- definition: `first_touch_atr_rr`
- horizon minutes: `180`
- ATR stop multiplier: `1.0`
- reward ratio: `1.0`

Real target selection: **NOT RUN**.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

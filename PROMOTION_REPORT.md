# Promotion Report

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Finalization state

- Synthetic promotion ready: **FALSE**.
- Synthetic result: `NO ROBUST EDGE FOUND`.
- Candidate exported: **NO**.
- Production promotion: **NO**.

Synthetic rejection reasons:

```json
[
  "ROC AUC is not above 0.5",
  "PR AUC does not beat class baseline",
  "too few OOS trades",
  "OOS portfolio return is not positive",
  "OOS portfolio profit factor is too low",
  "OOS mean selected-trade net return is not positive",
  "1.5x cost stress is not positive",
  "2x cost stress is negative",
  "walk-forward positive fold rate is below research minimum",
  "selected trades are concentrated in one strategy"
]
```

The full research runner never promotes automatically. Promotion is a separate explicit command that reruns registry gates:

```powershell
scripts\research_promote.cmd MODEL_VERSION
scripts\research_promote.cmd MODEL_VERSION --allow-schema-migration
```

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

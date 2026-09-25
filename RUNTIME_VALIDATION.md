# Runtime Validation

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Final package validation

- Backend/ML source and contracts: **PASS** through regression/static tests.
- Docker runtime after the final research-only overlay: **NOT RUN** in this environment.
- Live exchange runtime: **NOT RUN**.

The final overlay changes `ml_trainer` research persistence and adds research tooling; it does not intentionally change the already validated backend/ML serving protocol.

Local offline runtime validation command:

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFY_AND_REBUILD.ps1
```

Live Binance smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\runtime_smoke_test.ps1
```

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

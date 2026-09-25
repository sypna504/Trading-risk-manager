# Docker Validation

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Static Docker/Compose validation

- `docker-compose.yml` parsed during `check_patch_consistency.py`: **PASS**.
- Services `backend`, `ml_service`, `ml_trainer`: **PASS**.
- application-aware ML healthcheck contract: **PASS**.
- persistent SQLite named volume: **PASS**.
- trainer data/model mounts: **PASS**.
- research output mount `./runtime:/app/runtime`: **PASS**.
- `ML_RESEARCH_ROOT=/app/runtime/research`: **PASS**.
- Docker build: **NOT RUN**; Docker CLI is unavailable in packaging environment.
- Docker runtime: **NOT RUN**.

Build/runtime command:

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFY_AND_REBUILD.ps1
```

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

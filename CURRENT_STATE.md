# Current State

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Status

- Research implementation: **PASS** for static/unit/regression/synthetic validation.
- Regression tests: **15 passed / 0 failed**.
- ML/training tests: **117 passed / 0 failed**.
- Integration tests: **1 skipped / 0 failed** because environment-dependent runtime integration is not available in the packaging sandbox.
- Protobuf source contract: **PASS**.
- Generated protobuf strict check: **NOT RUN** because `grpcio-tools` is not installed in the packaging Python runtime; it is pinned in project requirements and generated during Docker build.
- Synthetic research: **PASS**, `17` experiments, result `NO ROBUST EDGE FOUND`.
- Docker build/runtime: **NOT RUN** because Docker CLI is unavailable in this environment.
- Real `history_data.parquet` research: **NOT RUN**.
- Real v3 improvement: **NOT PROVEN**.

The package is an overlay and deliberately does not ship real training data, active model binaries, registry state or SQLite data.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

## Package verification

A clean extraction of the packaged overlay was able to run the official suite and deterministic synthetic research without manual path edits. Final delivery is re-zipped and retested after report/manifest updates.

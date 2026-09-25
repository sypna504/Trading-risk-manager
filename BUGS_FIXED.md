# Bugs Fixed / Finalization Changes

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

Finalization did not add new trading hypotheses. It only closed concrete deliverable/runtime blockers in the frozen research implementation:

- persisted research outputs through `./runtime:/app/runtime` and `ML_RESEARCH_ROOT=/app/runtime/research`;
- added deterministic Docker synthetic-research entrypoint;
- added full-research/result/candidate/promotion CMD+SH wrappers;
- added explicit `NO ROBUST EDGE FOUND` result semantics;
- allowed the synthetic validation fixture to use CSV without requiring local parquet engines; real production research remains parquet-based;
- retained fail-closed candidate export/promotion behavior;
- expanded patch consistency checks for research scripts and mounts;
- documented application, tests, research, candidate checks, schema migration, status and rollback.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

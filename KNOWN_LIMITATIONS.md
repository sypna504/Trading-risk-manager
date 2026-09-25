# Known Limitations

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

1. Real Binance dataset research is **NOT RUN** in the packaging environment.
2. Real v3 improvement is **NOT PROVEN**.
3. Docker build/runtime is **NOT RUN** here because Docker CLI is unavailable.
4. Generated protobuf strict regeneration is **NOT RUN** in the packaging Python runtime because `grpcio-tools` is not installed there; it is pinned in requirements and generated during Docker build/clean-install validation.
5. Live exchange smoke and browser E2E are environment-dependent and **NOT RUN** here.
6. The current active model and registry are intentionally not replaced by this overlay.
7. The research candidate is never auto-promoted; manual promotion remains gate-protected.
8. Production trading remains **NO** until a v3 candidate passes real OOS research and subsequent live paper trading.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

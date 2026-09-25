# Test Report

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Actually executed

| Check | Result |
|---|---|
| `compileall app tests scripts` | PASS |
| dependency contract | PASS |
| settings contract | PASS |
| patch consistency | PASS |
| protobuf source contract | PASS |
| regression suite | **15 passed / 0 failed** |
| ML/training suite | **117 passed / 0 failed** |
| integration suite | **0 failed / 1 skipped** |
| synthetic research end-to-end | PASS, **17 experiments** |

The synthetic research completed with `research_result=NO ROBUST EDGE FOUND` and did not export/promote a candidate.

## Not run

- Docker build/up: Docker CLI unavailable.
- live Binance/Bybit requests.
- full research against the user's latest `history_data.parquet`.
- browser E2E.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```

## Additional finalization checks

- standalone frozen research regression module: **9 passed / 0 failed** (`pytest -q app/ml_services/app/training/tests/test_research_pipeline.py`)
- `docker-compose.yml` YAML parse + research mount assertions: **PASS**
- all shipped `scripts/*.sh` checked with `bash -n`: **PASS**
- final deterministic synthetic research module: **PASS**, **17 experiments**, `NO ROBUST EDGE FOUND`, no candidate exported

## First packed-archive verification

The first `research-final-v10` ZIP candidate was extracted into a clean directory and retested:

- `python scripts/test_all.py`: **PASS**
- regression: **15 passed / 0 failed**
- ML/training: **117 passed / 0 failed**
- integration: **1 skipped / 0 failed**
- standalone research regression: **9 passed / 0 failed**
- unpacked synthetic research: **PASS**, 17 experiments, `NO ROBUST EDGE FOUND`
- unpacked compose/script/report assertions: **PASS**

The final ZIP is regenerated after documentation/manifest updates and is retested again before delivery.

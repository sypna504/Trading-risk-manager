# Test Report — MVP-5

Date: 2026-09-25

## Executed locally

- Python compile for packaged MVP news/frontend sources: PASS.
- `pytest -q tests/news tests/frontend`: **49 passed / 0 failed**.
- ZIP extraction / compile / package consistency: performed during final packaging.
- Docker CLI: unavailable in the execution sandbox.

## Existing GitHub Actions on MVP-4 commit

Commit: `1588a49f35c9282aa8f8df6957ffe062b0502125`.

- compile: PASS
- backend-smoke: PASS
- docker-build (`backend`, `ml_service`, `ml_trainer`): PASS
- unit-regression: FAIL before execution of ML tests because the job did not set `PYTHONPATH=app/ml_services`
- ml-synthetic: 2 failures caused by pandas 3 categorical dtype no longer being plain `object`

The two ML failures are addressed by `MVP5_REGRESSION_FIX.patch`. The proposed `.github/workflows/ci.yml` runs the official `python scripts/test_all.py`, a dedicated ML job with correct `PYTHONPATH`, a news/frontend job, Docker build/runtime health, and a package/unpacked re-test job.

## Live systems

- Live Binance: NOT RUN
- Live Telegram: NOT RUN
- Live Ollama: NOT RUN

These are intentionally excluded from offline CI.

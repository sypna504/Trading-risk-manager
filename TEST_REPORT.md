# Test report

## Environment

- OS: Linux container
- Python: 3.13.5
- Docker: unavailable
- Internet/live exchanges: not used

## Commands and results

### Compilation

```bash
python -m compileall -q app tests ml
```

Result: PASS, no syntax errors.

### Smoke and audit regression tests

```bash
PYTHONPATH=.:app pytest -q tests/smoke tests/audit -W error::ResourceWarning
```

Result:

```text
28 passed
```

`ResourceWarning` is treated as an error; this specifically validates that SQLite connections are no longer leaked in covered flows.

### Diagnostic coverage

```bash
PYTHONPATH=.:app pytest -q tests/smoke tests/audit \
  --cov=app.backend.api.app.services.market_services \
  --cov=app.backend.api.app.services.signal_service \
  --cov=app.backend.api.app.services.risk_service \
  --cov=app.backend.api.app.services.model_metadata_service \
  --cov=app.backend.api.app.storage.database \
  --cov=app.backend.api.app.storage.decision_repository \
  --cov=app.backend.api.app.routers.trade_decision_router \
  --cov=app.ml_services.app.features_builder \
  --cov=app.ml_services.app.online.validation \
  --cov=app.ml_services.app.online.model_predictor \
  --cov-report=term-missing
```

Result: 28 passed, selected-module total coverage 65%.

Coverage is diagnostic, not a claim that the entire repository has 65% coverage. Full training/Docker/live paths were not executed.

## Test categories included in patch

- market closed-candle and data-normalization regression;
- latest feature row consistency;
- active model metadata resolution;
- risk boundary tests;
- partial multi-strategy failure and tie handling;
- gRPC finite-value validation;
- model predictor reload guard;
- SQLite concurrency/resource closure;
- deployment/configuration contract.

## Not executed

- Docker marker tests;
- browser Playwright tests;
- live exchange tests;
- expensive full CatBoost training;
- real candidate promotion and rollback.

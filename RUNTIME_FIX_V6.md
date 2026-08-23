# Runtime fix v6

## Confirmed failures

### 1. PowerShell quoting corrupted inline Python

The old `VERIFY_AND_REBUILD.ps1` passed a multiline Python program through
`python -c`. On Windows the quotes around `"1h"` were removed, producing:

```text
assert c.supported_intervals == [1h]
SyntaxError: invalid decimal literal
```

v6 does not pass Python source through command-line quoting. It runs real Python
modules/files inside the containers.

### 2. ML Settings did not define MIN_CANDLES

`online/validation.py` referenced `settings.MIN_CANDLES`, but the ML service
`Settings` class did not contain that field. This caused gRPC `UNKNOWN` and a
backend HTTP 502 response.

v6 adds `MIN_CANDLES=60` to ML settings and makes request validation use the
shared feature-builder constant.

## Additional runtime failure classes covered

- stale generated protobuf in one of the images;
- backend and ML images built from different contracts;
- incompatible scikit-learn version for the persisted calibrator;
- missing calibrator artifact;
- invalid model checksum;
- CatBoost model/config feature order mismatch;
- legacy v2 model missing `hour` or `weekday` at inference;
- unsupported timeframe sent to a 1h-only model;
- gRPC port bind failure;
- backend starting before ML is ready;
- backend reading a baked/stale model registry after retraining;
- external exchange failure being confused with an ML runtime failure.

## New checks

`VERIFY_AND_REBUILD.ps1` now performs:

1. host-file contract validation;
2. Compose syntax validation;
3. clean image rebuild;
4. trainer feature/protobuf/dependency checks;
5. active model + calibrator synthetic prediction;
6. backend protobuf and signal-builder checks;
7. ML health wait;
8. direct backend -> gRPC -> model probe without Binance or Bybit.

`scripts/runtime_smoke_test.ps1` then checks the public API and separately tests
that unsupported intervals are rejected.

`scripts/diagnose_runtime.ps1` creates a reusable diagnostics report with
versions, registry, files, logs, container state and direct gRPC results.

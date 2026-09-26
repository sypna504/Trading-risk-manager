# v10.2 audit/smoke compatibility fix

Date: 2026-08-25
Base: research-mvp v10.1 overlay on branch `feature/auto-signal-choseing`

## Why this patch exists

The full local `scripts/test_all.py` reached legacy `tests/audit` and `tests/smoke`
after the Windows UTF-8 fix. Those tests exposed real backward-compatibility issues
plus two stale test expectations.

## Runtime fixes

- gRPC validator reads `settings.MIN_CANDLES` dynamically instead of a module-import constant.
- generic `latest_complete_feature_row` is strict again; explicit offline fallback remains in
  `latest_complete_training_row`.
- signal-service regime fields are monitoring context and no longer prevent validation of the
  core latest signal row when an older fixture omits them.
- model predictor checks model-feature NaN/inf before request metadata validation.
- legacy outcome calculation defaults a missing interval to `1h` and reports an anchored
  insufficient-horizon error clearly.
- repository fills safe legacy defaults for new NOT NULL outcome/target columns.
- strategy evaluation tolerates one failed strategy, preserves deterministic tie-break, rejects
  mixed model versions, and accepts old response objects without the new raw/calibration fields.
- legacy `/ml/prediction-quality` test responses are normalized to the expanded response schema.
- backend compose explicitly declares `MODEL_REGISTRY_PATH`.

## Test-contract updates

- dependency audit now checks the intended exact pins (`==`) instead of stale `>=` assertions.
- latest-row audit explicitly tests `latest_strict_inference_row`.
- trade endpoint smoke test mocks the model-compatibility boundary instead of disabling the
  production fail-closed check.

## Apply

Extract this ZIP over the repository root with replacement enabled.

Before running tests, repair the local gRPC package versions because installing only
`grpcio-health-checking` allowed pip to upgrade grpc/protobuf while leaving old grpcio-tools:

```powershell
python -m pip install --upgrade --force-reinstall `
  grpcio==1.81.1 `
  grpcio-tools==1.81.1 `
  grpcio-health-checking==1.81.1 `
  protobuf==6.33.5
```

Verify:

```powershell
python -c "import grpc, google.protobuf, importlib.metadata as m; print(grpc.__version__); print(google.protobuf.__version__); print(m.version('grpcio-tools')); print(m.version('grpcio-health-checking'))"
python .\scripts\test_all.py
```

Expected versions: 1.81.1 / 6.33.5 / 1.81.1 / 1.81.1.

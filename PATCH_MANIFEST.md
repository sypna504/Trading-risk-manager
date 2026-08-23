# Patch manifest v6

## Runtime fixes

- `app/ml_services/app/config.py`
- `app/ml_services/app/online/validation.py`
- `app/ml_services/app/online/model_predictor.py`
- `app/ml_services/app/online/server.py`
- `app/ml_services/app/training/runtime_contract_check.py`
- `app/ml_services/app/training/train_model.py`
- `app/backend/api/app/config.py`
- `app/backend/api/app/grpc_client.py`
- `app/backend/api/app/routers/ml_service_router.py`
- `app/backend/api/app/schemas/ml_schemas.py`
- `app/backend/api/app/services/signal_service.py`

## Docker and verification

- `docker-compose.yml`
- `app/ml_services/dockerfile`
- `app/backend/api/dockerfile`
- `VERIFY_AND_REBUILD.ps1`
- `scripts/verify_backend_runtime.py`
- `scripts/grpc_runtime_probe.py`
- `scripts/runtime_smoke_test.ps1`
- `scripts/diagnose_runtime.ps1`

## Tests

- `app/ml_services/app/training/tests/test_runtime_failures_v6.py`
- updated `test_config_and_server.py`

The rest of the v3 quant pipeline from v5 remains included.

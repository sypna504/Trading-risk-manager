#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python scripts/check_dependency_contract.py
python scripts/check_settings_contract.py
python scripts/check_proto_contract.py
docker compose config --quiet
docker compose down --remove-orphans
docker compose build --no-cache ml_service ml_trainer backend
docker compose --profile training run --rm -e RUNTIME_CHECK_ACTIVE_MODEL=1 ml_trainer python -m app.training.runtime_contract_check
docker compose run --rm --no-deps backend python ./scripts/verify_backend_runtime.py
docker compose up -d --wait --wait-timeout 120 ml_service backend
docker compose ps
docker compose exec -T backend python ./scripts/grpc_runtime_probe.py
docker compose exec -T backend python ./scripts/sqlite_persistence_probe.py write
docker compose down
docker compose up -d --wait --wait-timeout 120 ml_service backend
docker compose exec -T backend python ./scripts/sqlite_persistence_probe.py read-clean
printf '%s\n' 'Docker offline validation complete; live exchange checks NOT RUN.'

# Docker validation

## Static validation performed

`docker-compose.yml` was parsed successfully as YAML. The following contracts were checked:

- services: `backend`, `ml_service`, `ml_trainer`;
- backend depends on healthy `ml_service`;
- backend address is `ml_service:50051`, not localhost;
- backend has persistent `backend_data:/app/data`;
- backend mounts model registry/model artifacts read-only;
- ML service and trainer share model and training-data bind mounts;
- expected ports are exposed;
- trainer is behind the `training` profile.

## Runtime validation status

Actual Docker commands were **not executed**, because the audit runtime has no `docker` executable.

Run after applying the patch:

```powershell
docker compose down -v
docker compose config
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose logs --tail=200 backend ml_service
```

Expected:

- `ml_service` becomes healthy;
- backend starts after ML health;
- `GET http://127.0.0.1:8000/api/v1/health` returns 200;
- response reports actual active `model_version`;
- SQLite file is located in the `backend_data` volume;
- restart does not remove decision history.

Persistence check:

```powershell
curl "http://127.0.0.1:8000/api/v1/trading/decisions?limit=5"
docker compose restart backend
curl "http://127.0.0.1:8000/api/v1/trading/decisions?limit=5"
```

Model/trainer check:

```powershell
docker compose --profile training run --rm ml_trainer --status
docker compose --profile training run --rm ml_trainer --mode manual
```

Do not merge until these commands pass on the target machine.

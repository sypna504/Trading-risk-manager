# Runtime failure matrix — research-mvp-final-v9

Ниже перечислены практические точки отказа текущего Docker/FastAPI/gRPC/ML
пути и проверка, которая должна их обнаруживать.

| Участок | Возможная причина | Симптом | Проверка |
|---|---|---|---|
| Docker build backend | `/app` отсутствует в `sys.path` при запуске script file | `No module named ml` или `No module named app` | Dockerfile задаёт `PYTHONPATH` до RUN; build import smoke |
| Protobuf package | отсутствуют `__init__.py`, файлы не созданы или stale | import error / отсутствуют новые response fields | package markers, `test -s`, descriptor verification |
| Backend/ML proto mismatch | images сгенерированы из разных proto | unknown fields, serialization errors | обе images генерируют proto из одного файла после COPY |
| ML settings | нет `MIN_CANDLES` | gRPC `UNKNOWN: Settings has no attribute MIN_CANDLES` | static contract и validator tests |
| Feature contract | старый `features_builder.py` | old fields, `hour/weekday`, missing interval | host regex + runtime contract v3 |
| Backend signal contract | старая сигнатура `latest_complete_feature_row` | positional argument TypeError | backend verifier synthetic signal test |
| Active registry path | Windows separators, traversal, stale path | model/config not found | portable path resolver + active bundle check |
| Active artifacts | model/config/calibrator отсутствуют | startup or precondition failure | runtime active-model check and diagnostics |
| Model/config mismatch | порядок/имена features различаются | CatBoost predict error | `feature_names_` compared with config |
| Model checksum | повреждён model.cbm | checksum error | predictor checksum validation |
| Calibrator | incompatible sklearn/pickle | warning or unpickle failure | sklearn pinned to 1.8.0 + active model load |
| Probability output | NaN/inf/outside 0..1 | INTERNAL or invalid API response | predictor and gRPC probe validation |
| Unsupported interval | 1h model receives 1m | invalid inference | model config compatibility check / HTTP 400 |
| gRPC readiness | ML server not listening | backend 502 | healthcheck + direct synthetic gRPC probe |
| Backend startup | dependencies or imports fail | backend container exits | backend image verifier and logs |
| Volume mount | host models directory not shared | missing registry/model in container | diagnostics: mounts, paths, registry, find |
| Port conflict | ports 8000/50051 occupied | container bind error | diagnostics and `docker compose ps -a` |
| Exchange access | Binance/Bybit timeout, DNS, regional block | public endpoint fails while direct gRPC succeeds | direct probe separates ML from exchange |
| Candle data | fewer than 60, duplicate timestamps, invalid OHLC | INVALID_ARGUMENT / HTTP 400/502 | validator and market-data checks |
| Docker cache | old files remain in image | mismatch between host and container | `--no-cache`, generated files removed after COPY |
| PowerShell quoting | quotes removed inside `python -c` | Python SyntaxError such as `[1h]` | no multiline Python passed from host shell |

`VERIFY_AND_REBUILD.ps1` checks build/import/model compatibility without
Binance or Bybit. `runtime_smoke_test.ps1` adds live exchange endpoints.
`diagnose_runtime.ps1` writes environment, image, volume, generated protobuf,
registry, model and gRPC details to a timestamped report.

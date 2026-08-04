# Functional validation

| Компонент | Сценарий | Фактическая проверка | Результат |
|---|---|---|---|
| Python modules | Compile all application/test modules | `python -m compileall -q app tests ml` | PASS |
| FastAPI | Load application and lifespan | TestClient smoke tests | PASS |
| Static frontend | `/`, CSS, JS | TestClient HTTP checks | PASS |
| OpenAPI | `/docs`, `/openapi.json` | TestClient HTTP checks | PASS |
| Health | backend response with mocked ML readiness | pytest smoke | PASS |
| Market service | closed-candle cutoff | synthetic exchange regression test | PASS |
| Market service | sort/dedupe/format validation | synthetic regression tests | PASS |
| Signal service | no signal | pytest smoke | PASS |
| Signal service | strict latest row | regression test | PASS |
| Trade decision | no-signal does not call ML | pytest smoke | PASS |
| Trade decision | evaluated flow | pytest smoke | PASS |
| Strategy selection | partial strategy failure | regression test | PASS |
| Strategy selection | deterministic equal probability | regression test | PASS |
| Strategy selection | mixed model versions | regression test | PASS |
| Risk engine | allowed/denied/no-signal | pytest smoke | PASS |
| Risk engine | non-finite/extreme ATR boundaries | regression tests | PASS |
| SQLite | initialization/save/list/get | pytest smoke | PASS |
| SQLite | concurrent writes and connection closure | audit tests + ResourceWarning strict mode | PASS |
| Model metadata | active registry + legacy fallback | regression tests | PASS |
| gRPC validation | NaN/inf/OHLC validation | regression tests | PASS |
| ModelPredictor | no repeated legacy reload | regression test | PASS |
| ModelPredictor | invalid numeric input | regression test | PASS |
| Compose contract | required services/volume/dependency | YAML static test | PASS |
| Docker images | actual build | Docker unavailable in runtime | NOT RUN |
| Docker health | actual containers | Docker unavailable in runtime | NOT RUN |
| Live Binance/Bybit | real network calls | excluded from deterministic suite | NOT RUN |
| Full retrain | real parquet/CatBoost candidate | incomplete runtime dependencies/artifacts | NOT RUN |
| Promotion/rollback | real registry + model binaries | static review only | PARTIAL |
| Browser e2e | real browser interaction | only static/API TestClient checks | PARTIAL |

# Bug report

## BUG-001 — blocker — protobuf/gRPC runtime incompatibility

**Компонент:** generated protobuf code / requirements

**Наблюдаемое поведение:** checked-in `ml_pb2_grpc.py` требует `grpcio >= 1.81.1`, а requirements фиксировал `grpcio==1.66.1`. Generated protobuf также создан runtime 6.33.5, тогда как backend ограничивал protobuf `<6`.

**Ожидаемое поведение:** чистая установка должна импортировать generated code без RuntimeError версии.

**Исправление:** зависимости согласованы: `grpcio>=1.81.1,<2`, `grpcio-tools>=1.81.1,<2`, `protobuf>=6.33.5,<7`.

**Regression test:** `tests/audit/test_deployment_contract.py`.

**Статус:** fixed.

---

## BUG-002 — critical — незакрытая свеча могла попадать в inference

**Компонент:** `market_services.py`

**Наблюдаемое поведение:** ответ биржи обрезался по limit, но текущая формирующаяся свеча не исключалась.

**Риск:** вероятность и сигнал могли меняться внутри свечи, а training использовал только закрытые свечи — train/inference skew.

**Исправление:** добавлено вычисление границы последней закрытой свечи, UTC-нормализация, сортировка, deduplication и фильтрация.

**Regression test:** `tests/audit/test_market_closed_candles.py`.

**Статус:** fixed.

---

## BUG-003 — critical — stale-feature fallback

**Компонент:** `features_builder.py`, `signal_service.py`

**Наблюдаемое поведение:** `dropna(...).iloc[-1]` мог выбирать более старую строку, когда последняя свеча имела неполные признаки.

**Риск:** API мог заявлять, что оценивает текущий рынок, фактически используя прошлую свечу.

**Исправление:** введена строгая проверка последней строки `latest_complete_feature_row`; неполная последняя строка теперь вызывает понятную ошибку.

**Regression test:** `tests/audit/test_latest_feature_row.py`.

**Статус:** fixed.

---

## BUG-004 — critical — backend показывал metadata legacy-модели вместо active registry model

**Компонент:** health/model-info

**Наблюдаемое поведение:** backend читал фиксированный legacy config, в то время как inference мог использовать модель из `registry.json`.

**Риск:** API показывал неверные `model_version`, threshold и train period.

**Исправление:** добавлен безопасный registry-aware resolver; backend получил read-only model mount и registry settings.

**Regression test:** `tests/audit/test_model_metadata.py`.

**Статус:** fixed.

---

## BUG-005 — critical — legacy predictor мог reload-ить модель на каждом запросе

**Компонент:** `ModelPredictor.reload`

**Наблюдаемое поведение:** при отсутствии active registry `registry_mtime=None`, ранний return не срабатывал.

**Риск:** лишний disk I/O и загрузка CatBoost на каждый inference, деградация latency и race risk.

**Исправление:** корректно сравниваются legacy paths и `None` mtime; reload выполняется только при реальном изменении.

**Regression test:** `tests/audit/test_model_predictor_reload.py`.

**Статус:** fixed.

---

## BUG-006 — major — NaN/inf проходили через gRPC validation

**Компонент:** `online/validation.py`

**Наблюдаемое поведение:** сравнения с NaN возвращают False, поэтому часть invalid candle values могла не abort-иться.

**Исправление:** явные `math.isfinite` проверки всех OHLCV; усилены OHLC invariants.

**Regression test:** `tests/audit/test_grpc_validation.py`.

**Статус:** fixed.

---

## BUG-007 — major — ModelPredictor не отклонял NaN и invalid probability

**Компонент:** `online/model_predictor.py`

**Наблюдаемое поведение:** проверялся `inf`, но не `NaN`; calibrator/model могли вернуть probability вне `[0,1]` или non-finite.

**Исправление:** полная finite-проверка features и итоговой probability.

**Regression test:** `tests/audit/test_model_predictor_reload.py`.

**Статус:** fixed.

---

## BUG-008 — major — один упавший strategy inference ломал весь dual-signal запрос

**Компонент:** `trade_decision_router.py`

**Наблюдаемое поведение:** при двух сигналах любой exception останавливал общий flow, даже если вторая стратегия была успешно оценена.

**Исправление:** каждый strategy call изолирован; успешный результат используется, ошибки сохраняются в reason; если упали все — возвращается 502.

**Regression test:** `tests/audit/test_strategy_selection.py`.

**Статус:** fixed.

---

## BUG-009 — major — неявное tie-breaking и сравнение разных model versions

**Компонент:** `trade_decision_router.py`

**Наблюдаемое поведение:** равные probabilities зависели от порядка списка; результаты разных версий модели могли сравниваться между собой при hot reload между gRPC-вызовами.

**Исправление:** детерминированный tie-break (`breakout`), mixed model versions отклоняются как неконсистентная оценка.

**Regression test:** `tests/audit/test_strategy_selection.py`.

**Статус:** fixed.

---

## BUG-010 — major — SQLite connections не закрывались гарантированно

**Компонент:** storage

**Наблюдаемое поведение:** контекстный менеджер `sqlite3.Connection` commit/rollback выполняет, но сам connection не закрывает. Это подтвердилось `ResourceWarning`.

**Исправление:** добавлен `connection_scope`, explicit close, WAL, busy timeout и synchronous=NORMAL.

**Regression test:** smoke/audit suite запускается с `-W error::ResourceWarning`; добавлен concurrent write test.

**Статус:** fixed.

---

## BUG-011 — major — SQLite не переживал пересоздание backend container

**Компонент:** `docker-compose.yml`

**Наблюдаемое поведение:** `DATABASE_PATH=/app/data/...`, но volume отсутствовал.

**Исправление:** named volume `backend_data:/app/data`.

**Regression test:** `tests/audit/test_deployment_contract.py` статически проверяет compose contract. Runtime persistence требует Docker validation.

**Статус:** fixed, runtime verification pending.

---

## BUG-012 — minor — сломанный/неиспользуемый strategy helper

**Компонент:** `signals/rules_for_strat.py`

**Наблюдаемое поведение:** опечатка `STRATAGIES`, отсутствовал return, возможен unbound local; двойной signal перезаписывался.

**Исправление:** возвращается список активных стратегий, сохранён backward-compatible alias.

**Статус:** fixed.

---

## BUG-013 — minor — неполная классификация pytest suite

**Компонент:** `pytest.ini`

**Наблюдаемое поведение:** markers из требований не были зарегистрированы.

**Исправление:** добавлены `unit`, `integration`, `docker`, `e2e`, `live`, `slow` markers.

**Статус:** fixed.

# Test report v6

Executed in the artifact environment:

```text
python -m compileall app scripts: passed
pytest app/ml_services/app/training/tests: 106 passed
runtime_contract_check with generated-contract stub: passed
YAML parse for docker-compose.yml: passed
```

New tests verify:

- ML settings contains `MIN_CANDLES=60`;
- validator accepts 60 candles and rejects 59;
- legacy inference columns remain available;
- v3 feature contract remains unchanged;
- model/config feature order validation does not break existing tests.

Not executed in this environment:

- Docker build, because Docker is unavailable here;
- live Binance/Bybit calls;
- prediction using the user's binary active model and calibrator.

Those checks are performed on the user's machine by
`VERIFY_AND_REBUILD.ps1` and `runtime_smoke_test.ps1`.

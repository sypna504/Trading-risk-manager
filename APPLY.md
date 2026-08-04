# Applying the audit patch

## 1. Create a safety branch

```powershell
git checkout feature/auto-signal-choseing
git pull
git checkout -b fix/total-functional-audit
```

## 2. Extract the archive

Extract the archive into the repository root and confirm file replacement.

## 3. Recreate dependencies

```powershell
python -m pip install -r app/backend/api/requirements.txt
python -m pip install -r app/ml_services/requirements.txt
python -m pip install -r requirements-test.txt
```

The grpc/protobuf versions were raised to match the checked-in generated code.

## 4. Run deterministic validation

```powershell
python -m compileall app tests
pytest -q tests/smoke tests/audit -W error::ResourceWarning
```

## 5. Validate Docker

```powershell
docker compose down -v
docker compose config
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose logs --tail=200 backend ml_service
```

## 6. Validate endpoints

```powershell
curl "http://127.0.0.1:8000/api/v1/health"
curl "http://127.0.0.1:8000/api/v1/ml/model-info"
curl "http://127.0.0.1:8000/api/v1/trading/decisions?limit=5"
```

For a live trading-decision check:

```powershell
curl "http://127.0.0.1:8000/api/v1/trading/decision?exchange=binance&symbol=BTCUSDT&interval=1h&limit=100&account_balance=1000&risk_per_trade_pct=1&max_position_share_pct=25"
```

## 7. Validate training lifecycle

```powershell
docker compose --profile training run --rm ml_trainer --status
docker compose --profile training run --rm ml_trainer --mode manual
```

## 8. Commit

```powershell
git add .
git commit -m "fix: harden signal inference, model lifecycle and deployment"
git push -u origin fix/total-functional-audit
```

## Rollback of patch

Before commit:

```powershell
git restore .
git clean -fd
```

After commit:

```powershell
git revert <commit-sha>
```

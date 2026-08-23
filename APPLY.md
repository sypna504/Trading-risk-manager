# Apply runtime fix v6

Extract the ZIP directly into the repository root and replace existing files.
Do not extract it into an extra nested directory.

## 1. Preserve the registry

```powershell
Copy-Item `
  .\app\ml_services\app\models\registry.json `
  .\app\ml_services\app\models\registry.json.bak
```

The archive itself does not contain or overwrite `registry.json`, active model
files, candidates, history parquet or the SQLite database.

## 2. Rebuild and verify

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFY_AND_REBUILD.ps1
```

This command rebuilds all three images and runs a direct synthetic prediction
through the active model. It does not require exchange connectivity.

## 3. Test API endpoints

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\runtime_smoke_test.ps1
```

The public prediction endpoints do require Binance connectivity.

## 4. Collect diagnostics after any failure

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnose_runtime.ps1
```

The report is saved under `scripts/runtime_diagnostics/`.

## 5. Train a v3 candidate

```powershell
scripts\retrain_v3_candidate_only.cmd
```

Only after checking its metrics:

```powershell
scripts\retrain_v3.cmd
```

## Expected runtime state

The old model may still appear as:

```text
risk_model_20260802_183813
feature_schema_version=legacy_v2
```

That is expected until a v3 candidate passes promotion. Runtime compatibility
with the old model does not mean that its trading quality has improved.

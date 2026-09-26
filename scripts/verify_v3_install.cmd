@echo off
setlocal
cd /d "%~dp0.."

echo [1/3] checking host files...
findstr /C:"FEATURE_SCHEMA_VERSION = \"v3\"" app\ml_services\app\features_builder.py >nul || (
  echo ERROR: project still contains the old features_builder.py
  echo Copy the archive contents directly into the repository root with replacement.
  exit /b 1
)
findstr /C:"\"interval\"," app\ml_services\app\features_builder.py >nul || (
  echo ERROR: interval is missing from FEATURE_COLUMNS
  exit /b 1
)

echo [2/3] rebuilding trainer image without cache...
docker compose build --no-cache ml_trainer || exit /b 1

echo [3/3] checking code inside the container...
docker compose --profile training run --rm ml_trainer python /app/../app/scripts/verify_v3_runtime.py 2>nul
if errorlevel 1 (
  rem Docker image contains /app/app but project scripts are not copied by the ML dockerfile.
  docker compose --profile training run --rm ml_trainer python -c "from app.features_builder import FEATURE_SCHEMA_VERSION,FEATURE_COLUMNS,CAT_FEATURES; from app.training.training_config import TrainingConfig; c=TrainingConfig.from_env(); assert FEATURE_SCHEMA_VERSION=='v3'; assert 'interval' in FEATURE_COLUMNS and 'interval' in CAT_FEATURES; assert 'hour' not in FEATURE_COLUMNS and 'weekday' not in FEATURE_COLUMNS; assert c.supported_intervals==['1h']; assert c.target_horizon_minutes==180; print('OK: runtime uses schema v3'); print('features=', len(FEATURE_COLUMNS)); print('supported_intervals=', c.supported_intervals); print('target_horizon_minutes=', c.target_horizon_minutes)" || exit /b 1
)

echo Verification completed successfully.
exit /b 0

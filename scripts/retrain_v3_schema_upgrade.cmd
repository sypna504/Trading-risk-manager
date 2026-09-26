@echo off
setlocal
cd /d "%~dp0.."
docker compose --profile training run --rm -e FORCE_RETRAIN=true -e ML_ALLOW_SCHEMA_MIGRATION=true ml_trainer python -m app.training.retrain_pipeline --mode manual --force --allow-schema-migration
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0.."
docker compose --profile training run --rm ml_trainer python -m app.training.retrain_pipeline --status
exit /b %ERRORLEVEL%

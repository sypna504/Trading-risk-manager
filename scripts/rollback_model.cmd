@echo off
setlocal
cd /d "%~dp0.."
docker compose --profile training run --rm ml_trainer python -m app.training.retrain_pipeline --rollback
if not "%ERRORLEVEL%"=="0" exit /b %ERRORLEVEL%
docker compose restart ml_service
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0.."
docker compose --profile training run --rm -e FORCE_RETRAIN=true ml_trainer
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0.."
docker compose --profile training run --rm -e FORCE_RETRAIN=true -e ML_CANDIDATE_ONLY=true ml_trainer
exit /b %ERRORLEVEL%

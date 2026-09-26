@echo off
setlocal
cd /d "%~dp0.."
docker compose --profile training run --rm ml_trainer python -m pytest app/training/tests -q
exit /b %ERRORLEVEL%

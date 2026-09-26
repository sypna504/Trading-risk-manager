@echo off
setlocal
docker compose --profile training run --rm ml_trainer python -m app.research.synthetic_runner
exit /b %ERRORLEVEL%

@echo off
setlocal
if "%~1"=="" (
  echo usage: scripts\research_promote.cmd MODEL_VERSION [--allow-schema-migration]
  exit /b 2
)
docker compose --profile training run --rm ml_trainer python -m app.research.promotion %*
exit /b %ERRORLEVEL%

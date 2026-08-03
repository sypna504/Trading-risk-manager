@echo off
setlocal

cd /d "%~dp0.."

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format ddMM"') do set MODEL_VERSION=%%i

if not exist logs mkdir logs

echo [%date% %time%] retrain started, version=risk_model_%MODEL_VERSION%>> logs\retrain.log

if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=%CD%\.venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

set PYTHONPATH=%CD%

%PYTHON_EXE% -m app.ml_services.app.training.retrain_pipeline >> logs\retrain.log 2>&1

if errorlevel 1 (
    echo [%date% %time%] retrain failed>> logs\retrain.log
    exit /b 1
)

echo [%date% %time%] retrain completed>> logs\retrain.log

echo Model files were updated. Rebuild or restart ml_service to load them.
exit /b 0

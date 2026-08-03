@echo off
setlocal

cd /d "%~dp0.."
set "PYTHONPATH=%CD%\app\ml_services"
if not defined ML_HISTORY_SYMBOL_POLICY set "ML_HISTORY_SYMBOL_POLICY=extend"

if "%~1"=="" (
    set "MODE=manual"
) else (
    set "MODE=%~1"
)

if exist "%CD%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m app.training.retrain_pipeline --mode %MODE%
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo Retrain pipeline failed with exit code %EXIT_CODE%.
    exit /b %EXIT_CODE%
)

echo Retrain pipeline completed.
exit /b 0

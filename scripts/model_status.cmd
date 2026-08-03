@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\app\ml_services"
if exist "%CD%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)
"%PYTHON_EXE%" -m app.training.retrain_pipeline --status
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\app\ml_services"
python -m pytest -q app\ml_services\app\training\tests
exit /b %ERRORLEVEL%

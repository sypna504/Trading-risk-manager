@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
python -m pytest -q tests\regression
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0.."
python scripts\test_all.py %*
exit /b %ERRORLEVEL%

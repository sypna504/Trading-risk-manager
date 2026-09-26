@echo off
setlocal
cd /d "%~dp0.."
python scripts\fix_registry_paths.py
exit /b %ERRORLEVEL%

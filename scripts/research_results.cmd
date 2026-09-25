@echo off
setlocal
python scripts\research_status.py
exit /b %ERRORLEVEL%

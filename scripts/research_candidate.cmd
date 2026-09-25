@echo off
setlocal
python scripts\research_status.py --candidate
exit /b %ERRORLEVEL%

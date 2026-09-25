@echo off
setlocal
cd /d "%~dp0.."
python scripts\generate_proto.py
exit /b %ERRORLEVEL%

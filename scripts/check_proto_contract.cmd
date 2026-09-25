@echo off
setlocal
cd /d "%~dp0.."
python scripts\check_proto_contract.py
exit /b %ERRORLEVEL%

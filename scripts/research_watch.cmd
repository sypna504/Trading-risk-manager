@echo off
setlocal
set "ROOT=%~1"
if "%ROOT%"=="" set "ROOT=runtime\research"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$path = Join-Path '%ROOT%' 'PROGRESS.jsonl';" ^
  "Write-Host ('Watching ' + $path);" ^
  "while (-not (Test-Path $path)) { Write-Host 'waiting for research progress file...'; Start-Sleep -Seconds 2 };" ^
  "Get-Content -Path $path -Tail 30 -Wait"
exit /b %ERRORLEVEL%

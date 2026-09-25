param(
    [switch]$WithLiveExchange,
    [switch]$SkipPersistenceCycle
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
& powershell -ExecutionPolicy Bypass -File .\VERIFY_AND_REBUILD.ps1 -SkipPersistenceCycle:$SkipPersistenceCycle
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($WithLiveExchange) {
    & powershell -ExecutionPolicy Bypass -File .\scripts\runtime_smoke_test.ps1
    exit $LASTEXITCODE
}
Write-Host "Docker offline validation complete. Live exchange checks: NOT RUN."

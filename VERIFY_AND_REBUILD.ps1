param(
    [switch]$SkipPersistenceCycle
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-Checked {
    param([string]$File, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$File $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Show-RuntimeLogs {
    Write-Host "`n--- docker compose ps ---" -ForegroundColor Yellow
    & docker compose ps
    Write-Host "`n--- ml_service/backend logs ---" -ForegroundColor Yellow
    & docker compose logs --tail 300 ml_service backend
}

function Wait-ContainerHealthy {
    param([string]$ContainerName, [int]$Attempts = 40)
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $health = (& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $ContainerName 2>$null)
        if ($health -eq "healthy") { return }
        if ($health -eq "unhealthy") {
            Show-RuntimeLogs
            throw "$ContainerName became unhealthy"
        }
        Start-Sleep -Seconds 2
    }
    Show-RuntimeLogs
    throw "$ContainerName did not become healthy"
}

$patchVersion = (Get-Content (Join-Path $PSScriptRoot "PATCH_VERSION.txt") -Raw).Trim()
if (-not $patchVersion) { throw "PATCH_VERSION.txt is empty" }
Write-Host "Patch: $patchVersion" -ForegroundColor Cyan

$required = @(
    "app\backend\api\app\config.py",
    "app\backend\api\app\services\model_compatibility.py",
    "app\backend\api\app\services\strategy_selection.py",
    "app\backend\api\app\services\outcome_service.py",
    "app\ml_services\app\features_builder.py",
    "app\ml_services\app\training\runtime_contract_check.py",
    "scripts\verify_backend_runtime.py",
    "scripts\grpc_runtime_probe.py",
    "scripts\sqlite_persistence_probe.py"
)
foreach ($path in $required) {
    if (-not (Test-Path (Join-Path $PSScriptRoot $path))) {
        throw "Patch file missing: $path. Extract the ZIP directly into the repository root with replacement."
    }
}

Write-Host "Running host contract checks..."
Invoke-Checked python scripts\check_dependency_contract.py
Invoke-Checked python scripts\check_settings_contract.py
Invoke-Checked python scripts\check_proto_contract.py
Invoke-Checked python -m compileall -q app scripts tests

Write-Host "Validating Compose..."
Invoke-Compose config --quiet

Write-Host "Removing old containers (volumes are preserved)..."
Invoke-Compose down --remove-orphans

Write-Host "Building backend/ML/trainer without cache..."
Invoke-Compose build --no-cache ml_service ml_trainer backend

Write-Host "Checking trainer image + active bundle..."
& docker compose --profile training run --rm -e RUNTIME_CHECK_ACTIVE_MODEL=1 ml_trainer python -m app.training.runtime_contract_check
if ($LASTEXITCODE -ne 0) {
    throw "Trainer image or active model contract failed. Inspect the JSON above."
}

Write-Host "Checking backend image contract..."
& docker compose run --rm --no-deps backend python ./scripts/verify_backend_runtime.py
if ($LASTEXITCODE -ne 0) {
    throw "Backend image/settings/protobuf/signal contract failed."
}

Write-Host "Starting services..."
Invoke-Compose up -d ml_service backend
Wait-ContainerHealthy "ml-services-grpc"
Wait-ContainerHealthy "python-fastapi-backend"

Write-Host "Running network-independent backend -> gRPC -> model probe..."
& docker compose exec -T backend python ./scripts/grpc_runtime_probe.py
if ($LASTEXITCODE -ne 0) {
    Show-RuntimeLogs
    throw "Direct gRPC prediction probe failed"
}

Write-Host "Checking model-info endpoint..."
$modelInfo = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ml/model-info" -TimeoutSec 15
$modelInfo | ConvertTo-Json -Depth 12

if (-not $SkipPersistenceCycle) {
    Write-Host "Checking SQLite named-volume persistence across docker compose down/up..."
    Invoke-Compose exec -T backend python ./scripts/sqlite_persistence_probe.py write
    Invoke-Compose down
    Invoke-Compose up -d ml_service backend
    Wait-ContainerHealthy "ml-services-grpc"
    Wait-ContainerHealthy "python-fastapi-backend"
    Invoke-Compose exec -T backend python ./scripts/sqlite_persistence_probe.py read-clean
}

Write-Host "`nDocker build/runtime contract validation passed." -ForegroundColor Green
Write-Host "Live Binance/Bybit calls were NOT executed by this script."
Write-Host "Run .\scripts\runtime_smoke_test.ps1 for live-exchange endpoint validation."

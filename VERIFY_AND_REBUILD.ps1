$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Show-RuntimeLogs {
    Write-Host "`n--- ml_service/backend logs ---" -ForegroundColor Yellow
    & docker compose logs --tail 250 ml_service backend
}

$featuresPath = Join-Path $PSScriptRoot "app\ml_services\app\features_builder.py"
$configPath = Join-Path $PSScriptRoot "app\ml_services\app\config.py"
$runtimeCheckPath = Join-Path $PSScriptRoot "app\ml_services\app\training\runtime_contract_check.py"
$backendCheckPath = Join-Path $PSScriptRoot "scripts\verify_backend_runtime.py"

foreach ($requiredPath in @($featuresPath, $configPath, $runtimeCheckPath, $backendCheckPath)) {
    if (-not (Test-Path $requiredPath)) {
        throw "Required patch file is missing: $requiredPath. Extract the archive directly into the repository root with replacement."
    }
}

$features = Get-Content $featuresPath -Raw
$config = Get-Content $configPath -Raw
if ($features -notmatch 'FEATURE_SCHEMA_VERSION\s*=\s*"v3"') {
    throw "Old features_builder.py is still present."
}
if ($features -notmatch 'required_columns:\s*list\[str\]\s*\|\s*None') {
    throw "latest_complete_feature_row compatibility fix is missing."
}
if ($config -notmatch 'MIN_CANDLES:\s*int\s*=\s*60') {
    throw "ML Settings.MIN_CANDLES fix is missing."
}

Write-Host "Host files: runtime fix v6 found" -ForegroundColor Green

& docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw "docker-compose.yml is invalid" }

Invoke-Compose down --remove-orphans
Invoke-Compose build --no-cache ml_service ml_trainer backend

Write-Host "Checking trainer image and active model bundle..."
& docker compose --profile training run --rm -e RUNTIME_CHECK_ACTIVE_MODEL=1 ml_trainer python -m app.training.runtime_contract_check
if ($LASTEXITCODE -ne 0) {
    throw "Trainer image, active model, calibrator, protobuf, or feature contract is incompatible. See JSON output above."
}

Write-Host "Checking backend image, protobuf and signal feature contract..."
& docker compose run --rm --no-deps backend python ./scripts/verify_backend_runtime.py
if ($LASTEXITCODE -ne 0) {
    throw "Backend image, protobuf, settings, or signal feature contract is incompatible. See JSON output above."
}

Write-Host "Starting runtime services..."
Invoke-Compose up -d ml_service backend

$healthy = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $health = (& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' ml-services-grpc 2>$null)
    if ($health -eq "healthy") {
        $healthy = $true
        break
    }
    if ($health -eq "unhealthy") {
        Show-RuntimeLogs
        throw "ml_service became unhealthy"
    }
    Start-Sleep -Seconds 2
}
if (-not $healthy) {
    Show-RuntimeLogs
    throw "ml_service did not become healthy within 60 seconds"
}

Write-Host "Running direct gRPC probe without exchange/network dependency..."
& docker compose exec -T backend python ./scripts/grpc_runtime_probe.py
if ($LASTEXITCODE -ne 0) {
    Show-RuntimeLogs
    throw "Direct backend -> gRPC -> active model probe failed"
}

Write-Host "`nBuild and runtime compatibility checks passed." -ForegroundColor Green
Write-Host "Now run: powershell -ExecutionPolicy Bypass -File .\scripts\runtime_smoke_test.ps1"

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Show-Logs {
    Write-Host "`n--- docker compose ps ---" -ForegroundColor Yellow
    & docker compose ps
    Write-Host "`n--- ml_service/backend logs ---" -ForegroundColor Yellow
    & docker compose logs --tail 300 ml_service backend
}

function Get-ErrorBody {
    param($ErrorRecord)
    try {
        $response = $ErrorRecord.Exception.Response
        if ($null -eq $response) { return $ErrorRecord.Exception.Message }
        $stream = $response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        return $reader.ReadToEnd()
    }
    catch {
        return $ErrorRecord.Exception.Message
    }
}

function Invoke-JsonEndpoint {
    param(
        [string]$Name,
        [string]$Url
    )
    Write-Host "`nChecking $Name..."
    try {
        $result = Invoke-RestMethod -Uri $Url -TimeoutSec 60
        $result | ConvertTo-Json -Depth 12
        return $result
    }
    catch {
        $body = Get-ErrorBody $_
        Write-Host "$Name failed: $body" -ForegroundColor Red
        Show-Logs
        throw
    }
}

Write-Host "Starting services..."
& docker compose up -d ml_service backend
if ($LASTEXITCODE -ne 0) { throw "Could not start services" }

$ready = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ml/model-info" -TimeoutSec 3
        $ready = $true
        break
    }
    catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $ready) {
    Show-Logs
    throw "Backend did not become ready within 60 seconds"
}

Write-Host "`nChecking direct gRPC call with synthetic candles..."
& docker compose exec -T backend python ./scripts/grpc_runtime_probe.py
if ($LASTEXITCODE -ne 0) {
    Show-Logs
    throw "Direct gRPC probe failed. This is an ML runtime/config/model issue, not an exchange issue."
}

$modelInfo = Invoke-JsonEndpoint `
    -Name "model info" `
    -Url "http://localhost:8000/api/v1/ml/model-info"

if ($modelInfo.supported_intervals -notcontains "1h") {
    throw "Active model does not support 1h"
}

$prediction = Invoke-JsonEndpoint `
    -Name "prediction-quality" `
    -Url "http://localhost:8000/api/v1/ml/prediction-quality?exchange=binance&symbol=BTCUSDT&interval=1h&strategy_name=mean_reversion&limit=500"

$decision = Invoke-JsonEndpoint `
    -Name "trading decision" `
    -Url "http://localhost:8000/api/v1/trading/decision?exchange=binance&symbol=BTCUSDT&interval=1h&limit=500&account_balance=1000&risk_per_trade_pct=1&max_position_share_pct=25"

Write-Host "`nChecking unsupported interval rejection..."
try {
    $null = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ml/prediction-quality?exchange=binance&symbol=BTCUSDT&interval=1m&strategy_name=mean_reversion&limit=500" -TimeoutSec 60
    throw "1m request unexpectedly succeeded with a 1h-only model"
}
catch {
    $status = $null
    try { $status = [int]$_.Exception.Response.StatusCode } catch { }
    if ($status -ne 400 -and $status -ne 422) {
        $body = Get-ErrorBody $_
        Show-Logs
        throw "Unsupported interval returned unexpected status=$status body=$body"
    }
    Write-Host "Unsupported interval correctly rejected with HTTP $status" -ForegroundColor Green
}

Write-Host "`nRuntime smoke test completed." -ForegroundColor Green

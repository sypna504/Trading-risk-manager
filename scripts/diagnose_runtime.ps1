$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

$reportDir = Join-Path $PSScriptRoot "runtime_diagnostics"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $reportDir "diagnostics_$stamp.txt"

function Add-Section {
    param([string]$Title, [scriptblock]$Command)
    "`n===== $Title =====" | Tee-Object -FilePath $reportPath -Append
    try {
        & $Command 2>&1 | Out-String | Tee-Object -FilePath $reportPath -Append
    }
    catch {
        $_ | Out-String | Tee-Object -FilePath $reportPath -Append
    }
}

Add-Section "host patch version" {
    Get-Content .\PATCH_VERSION.txt -Raw
    Get-FileHash .\app\backend\api\dockerfile -Algorithm SHA256
    Get-FileHash .\app\ml_services\dockerfile -Algorithm SHA256
}
Add-Section "docker version" { docker version }
Add-Section "docker compose version" { docker compose version }
Add-Section "compose config" { docker compose config }
Add-Section "compose ps" { docker compose ps -a }
Add-Section "images" { docker images --digests }
Add-Section "ports 8000 and 50051" {
    Get-NetTCPConnection -LocalPort 8000,50051 -ErrorAction SilentlyContinue |
        Select-Object LocalAddress,LocalPort,State,OwningProcess
}
Add-Section "container mounts" {
    docker inspect python-fastapi-backend ml-services-grpc --format '{{.Name}} {{json .Mounts}}'
}
Add-Section "ml/backend logs" { docker compose logs --tail 500 ml_service backend }
Add-Section "trainer static/runtime contract" {
    docker compose --profile training run --rm -e RUNTIME_CHECK_ACTIVE_MODEL=1 ml_trainer python -m app.training.runtime_contract_check
}
Add-Section "backend static contract" {
    docker compose run --rm --no-deps backend python ./scripts/verify_backend_runtime.py
}
Add-Section "backend sys.path and generated protobuf" {
    docker compose run --rm --no-deps backend sh -lc 'echo PYTHONPATH=$PYTHONPATH; python -c "import sys; print(sys.path); from ml.v1 import ml_pb2, ml_pb2_grpc; print(ml_pb2.__file__); print(ml_pb2_grpc.__file__)"; find /app/ml -maxdepth 3 -type f -print'
}
Add-Section "ML sys.path and generated protobuf" {
    docker compose --profile training run --rm ml_trainer sh -lc 'echo PYTHONPATH=$PYTHONPATH; python -c "import sys; print(sys.path); from ml.v1 import ml_pb2, ml_pb2_grpc; print(ml_pb2.__file__); print(ml_pb2_grpc.__file__)"; find /app/ml -maxdepth 3 -type f -print'
}
Add-Section "active registry on host" {
    Get-Content .\app\ml_services\app\models\registry.json -Raw
}
Add-Section "active model files in ML container" {
    docker compose exec -T ml_service sh -lc 'ls -la /app/app/models; find /app/app/models/active -maxdepth 3 -type f -print; cat /app/app/models/registry.json'
}
Add-Section "ML package versions" {
    docker compose exec -T ml_service python -c "import sys, sklearn, catboost, pandas, numpy, grpc; print(sys.version); print('sklearn', sklearn.__version__); print('catboost', catboost.__version__); print('pandas', pandas.__version__); print('numpy', numpy.__version__); print('grpc', grpc.__version__)"
}
Add-Section "direct gRPC probe" {
    docker compose exec -T backend python ./scripts/grpc_runtime_probe.py
}

Write-Host "Diagnostics saved to $reportPath" -ForegroundColor Green

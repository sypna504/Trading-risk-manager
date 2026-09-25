$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker run --rm `
  -v "${PWD}:/src" `
  -w /src `
  python:3.11-slim `
  sh -lc "python -m pip install --upgrade pip && python -m pip install --no-cache-dir -r requirements-test.txt && python scripts/generate_proto.py --output /tmp/trm_proto && PYTHONPATH=/tmp/trm_proto:/src python scripts/test_all.py --strict-environment"

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

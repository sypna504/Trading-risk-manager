#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm \
  -v "$(pwd):/src" \
  -w /src \
  python:3.11-slim \
  sh -lc 'python -m pip install --upgrade pip && python -m pip install --no-cache-dir -r requirements-test.txt && python scripts/generate_proto.py --output /tmp/trm_proto && PYTHONPATH=/tmp/trm_proto:/src python scripts/test_all.py --strict-environment'

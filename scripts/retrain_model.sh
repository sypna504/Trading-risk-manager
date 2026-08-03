#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

export MODEL_VERSION="${MODEL_VERSION:-$(date +%d%m)}"
export PYTHONPATH="$ROOT_DIR"
mkdir -p logs

PYTHON_EXE="python"
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_EXE="$ROOT_DIR/.venv/bin/python"
fi

printf '[%s] retrain started, version=risk_model_%s\n' "$(date -Iseconds)" "$MODEL_VERSION" >> logs/retrain.log

if "$PYTHON_EXE" -m app.ml_services.app.training.retrain_pipeline >> logs/retrain.log 2>&1; then
  printf '[%s] retrain completed\n' "$(date -Iseconds)" >> logs/retrain.log
else
  printf '[%s] retrain failed\n' "$(date -Iseconds)" >> logs/retrain.log
  exit 1
fi

echo "Model files were updated. Rebuild or restart ml_service to load them."

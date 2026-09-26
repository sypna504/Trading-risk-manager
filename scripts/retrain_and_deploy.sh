#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT/app/ml_services${PYTHONPATH:+:$PYTHONPATH}"
export ML_HISTORY_SYMBOL_POLICY="${ML_HISTORY_SYMBOL_POLICY:-extend}"
MODE=${1:-manual}

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PYTHON_EXE="$REPO_ROOT/.venv/bin/python"
else
  PYTHON_EXE=python
fi

"$PYTHON_EXE" -m app.training.retrain_pipeline --mode "$MODE"

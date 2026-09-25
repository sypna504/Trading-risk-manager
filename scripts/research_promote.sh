#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
  echo "usage: scripts/research_promote.sh MODEL_VERSION [--allow-schema-migration]" >&2
  exit 2
fi
docker compose --profile training run --rm ml_trainer python -m app.research.promotion "$@"

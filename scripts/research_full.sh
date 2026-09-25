#!/usr/bin/env sh
set -eu
docker compose --profile training run --rm ml_trainer python -m app.research.runner --mode full --update-history

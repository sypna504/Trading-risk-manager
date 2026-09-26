#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
exec python scripts/test_all.py "$@"

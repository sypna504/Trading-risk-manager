#!/usr/bin/env sh
set -eu
ROOT="${1:-runtime/research}"
PATH_TO_PROGRESS="$ROOT/PROGRESS.jsonl"
echo "Watching $PATH_TO_PROGRESS"
while [ ! -f "$PATH_TO_PROGRESS" ]; do
  echo "waiting for research progress file..."
  sleep 2
done
tail -n 30 -f "$PATH_TO_PROGRESS"

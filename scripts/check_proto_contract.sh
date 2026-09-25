#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python scripts/check_proto_contract.py

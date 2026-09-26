#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
for name in \
  AUDIT_REPORT.md BUG_REPORT.md CHANGES.md EXECUTIVE_SUMMARY.md \
  FUNCTIONAL_VALIDATION.md MODEL_AUDIT.md PROMOTION_VALIDATION.md \
  RUNTIME_FIX.md RUNTIME_FIX_V6.md RUNTIME_FIX_V7.md \
  VALIDATION_RESULTS.md TEST_RESULTS.txt .env.example.outcome-additions
do
  if [ -f "$name" ]; then
    rm -f "$name"
    printf 'removed stale file: %s\n' "$name"
  fi
done

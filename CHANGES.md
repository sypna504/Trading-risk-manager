# Audit patch changes

## Backend

- hardened candle normalization and filtering;
- added strict latest-feature behavior;
- added registry-aware model metadata service;
- health and model-info now report active model;
- hardened risk calculation;
- made dual-strategy selection deterministic and failure-tolerant;
- rejected mixed model-version comparisons;
- fixed SQLite connection lifetime and concurrency settings;
- added persistent SQLite/model mounts in Compose.

## ML service

- added strict input validation in feature builder;
- hardened gRPC validation against NaN/inf and invalid OHLC;
- fixed legacy model reload behavior;
- hardened model configuration, feature and probability validation;
- fixed strategy helper behavior;
- aligned protobuf/gRPC package versions with generated code.

## Tests

Added `tests/audit/` regression tests for every confirmed bug category.

## Configuration

- added backend model-root and registry variables;
- added inference aliases to `.env.example`;
- registered pytest test markers;
- added `backend_data` volume.

## Compatibility notes

- dependency upgrade requires rebuilding Python environments and Docker images;
- backend model-info now follows active registry when available, falling back to legacy paths;
- dual strategy equality is now explicitly resolved in favor of `breakout`;
- when one strategy fails and another succeeds, the successful strategy is used and the failure is included in `reason`;
- mixed model versions in one decision are treated as a 502 consistency error.

# ML validation

## Reviewed and locally validated

### Feature/inference consistency

- training and inference continue to use one `features_builder`;
- rolling high values remain shifted by one bar;
- latest inference feature row must correspond to the latest supplied candle;
- non-finite input is rejected;
- current unclosed candle is filtered before inference.

### gRPC validation

- candle count comes from ML settings;
- OHLCV must be finite;
- OHLC must be positive and internally consistent;
- volume must be non-negative;
- timestamp ordering/duplicates remain validated.

### Model loading

- active artifacts are resolved relative to a model root;
- absolute paths, drive letters and traversal are rejected;
- checksum is validated when present;
- failed hot reload retains the previous loaded model;
- legacy mode no longer reloads on every prediction;
- non-finite features and invalid probabilities are rejected.

### Training code review

The branch already contains:

- rolling training window;
- global chronological split;
- purge bars at split boundaries;
- validation partitioning for model selection, calibration and threshold;
- independent test evaluation;
- walk-forward reporting;
- calibration selection by Brier score;
- candidate/champion registry;
- promotion gate;
- atomic JSON writes and rollback artifacts;
- update-history guards and closed-candle cutoff.

## Risks still requiring execution

1. Full pipeline was not run on real parquet data.
2. Candidate/champion comparison was not executed with actual model binaries.
3. Promotion and rollback were not exercised through Docker shared volumes.
4. Walk-forward metrics were not independently recomputed.
5. Live exchange pagination was not tested against Binance/Bybit.
6. The checked-in active model quality was not revalidated; no claim of model improvement is made.

## Required full-pipeline commands

```powershell
docker compose --profile training run --rm ml_trainer --status
docker compose --profile training run --rm ml_trainer --mode manual --force
docker compose logs --tail=300 ml_service
curl "http://127.0.0.1:8000/api/v1/ml/model-info"
```

Then verify:

- training report exists;
- candidate decision contains reasons;
- rejected candidate does not change active version;
- promoted candidate changes registry atomically;
- next inference returns promoted `model_version`;
- rollback restores previous version.

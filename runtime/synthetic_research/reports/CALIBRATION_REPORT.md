# Calibration Report

- **generated_at:** 2026-08-26T20:03:13.730736+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** 1b31deeb587a7a087008478e8b0a8a73a9ea5b24b145022c6273706df91ba453
- **history_period:** 2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00
- **mode:** quick

{
  "__global__": {
    "selected": "none",
    "candidates": [
      {
        "method": "none",
        "brier": 0.20228945383707667,
        "ece": 0.17790771870334882,
        "std": 0.13729668541603635,
        "unique": 28,
        "valid": true
      },
      {
        "method": "platt",
        "brier": 0.17123122121832227,
        "ece": 0.05262020517643337,
        "std": 0.0009538481809555315,
        "unique": 28,
        "valid": false
      },
      {
        "method": "isotonic",
        "brier": 0.22532265560266646,
        "ece": 0.22315387097707723,
        "std": 0.18951151907001013,
        "unique": 5,
        "valid": false
      }
    ]
  }
}

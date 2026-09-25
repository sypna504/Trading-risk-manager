# Calibration Report

- **generated_at:** 2026-08-26T20:33:44.632613+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** bca733e890c181bd22c00649c34b49ebf85d1ffce353069401e83d26845505c2
- **history_period:** 2025-12-09 18:00:00+00:00 → 2026-08-26 19:00:00+00:00
- **mode:** full

{
  "__global__": {
    "selected": "none",
    "candidates": [
      {
        "method": "none",
        "brier": 0.24838039058347658,
        "ece": 0.14746016517037414,
        "std": 0.020590026589034166,
        "unique": 622,
        "valid": true
      },
      {
        "method": "platt",
        "brier": 0.2361413373843031,
        "ece": 0.08860709767401526,
        "std": 0.002132993729751805,
        "unique": 622,
        "valid": false
      },
      {
        "method": "isotonic",
        "brier": 0.2314902439863907,
        "ece": 0.08130798877932033,
        "std": 0.04727095704755681,
        "unique": 10,
        "valid": false
      }
    ]
  }
}

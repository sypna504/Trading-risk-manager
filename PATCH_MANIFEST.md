# Patch manifest

This archive contains only audit reports, regression tests, and files changed to fix confirmed defects in `feature/auto-signal-choseing`.

It intentionally does not include:

- model binaries;
- parquet datasets;
- SQLite databases;
- `.env`;
- Python caches;
- local generated protobuf test stubs;
- working-tree temporary files.

## Files and SHA-256

- `.env.example` — `bc2b0006c6111986c1629abc52c1324ceeed1ae042125f0100e6318338157490`
- `docker-compose.yml` — `86a29a29533395a98179a947dcc8037c71aefdf0f87bf4b101a032a1c5e484fc`
- `pytest.ini` — `21b6e7122dac6078993c1e4f8cec31f79f49de453a77da750db5bb27c32f9330`
- `app/backend/api/requirements.txt` — `eddc303f4d74c8cd56df11ea1ca27ba82b54ef57f17407186ced4561a5f938e9`
- `app/ml_services/requirements.txt` — `3acaa6cc967e5d119f3c14248ca12133b4d076bbe0d5cbd8587ceb818749afc6`
- `app/backend/api/app/config.py` — `d2d2703c1084961f69b55ac03174dbdac767f4a294a3020f15b9de2de8064ffc`
- `app/backend/api/app/services/market_services.py` — `363da0a93b89a58b558cc6688df39562875bfb456caed949cb38c0185b6bb2c7`
- `app/ml_services/app/features_builder.py` — `e3184e7e6aa8de98851a9baa362134a67bb195ab4240df01e45a7c84a1b363c3`
- `app/backend/api/app/services/signal_service.py` — `757984a377e8fda6b01e3b84d91398df6cd5d14f2a5359f1d9689c5dfd7049e3`
- `app/backend/api/app/services/model_metadata_service.py` — `0f25520b523e52d043277ad09cceab9c8c7d0e66d0617eaa4bd0836d02920902`
- `app/backend/api/app/routers/health_router.py` — `9727b19f4e2fb4eab9cb5256e363735748f5c9bbbeedf2a91379e12d54b6b2b9`
- `app/backend/api/app/routers/ml_service_router.py` — `cf94c92a1243aa3884fcb7e03dc8211e8adb8de970236ec6fabc474feb01cff3`
- `app/backend/api/app/services/risk_service.py` — `aeadc81e6afaebefabd7e922135c45908548d4a72a459340c2e2cc590d1bec68`
- `app/backend/api/app/routers/trade_decision_router.py` — `f0aab126b337a54983e981374655053e70c1439b976b7dfeaf2fb6912ccbfb96`
- `app/backend/api/app/storage/database.py` — `5b4c54651001ba0ee0f92163deafa57d0d20e033e1ec296e89f3299942c953f7`
- `app/backend/api/app/storage/decision_repository.py` — `57b09db454d86a5c7d5926092313bc7baa1e7539c4f682ee0a7739bc56e75d66`
- `app/ml_services/app/config.py` — `0f8f33badafbf54f8c9c072a26db0182c251dcbf1118d3339596c639c62fd123`
- `app/ml_services/app/online/validation.py` — `070b6ee91ac2f437f36a7e1e54964ee737324ec902b758c3b09ef4e98b66042a`
- `app/ml_services/app/online/model_predictor.py` — `108502bdce33daadebb63d202270619c9ffd0520fb9326c86a7bf065e1d31b1f`
- `app/ml_services/app/online/ml_inference.py` — `de367e6847c849936e2734ed33247520e0e88b78579cc385f0cef75d341738a1`
- `app/ml_services/app/signals/__init__.py` — `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `app/ml_services/app/signals/rules_for_strat.py` — `870f60072b5bbd35d10587bce42cdd138fb8c5dc758113abfb03219886de60bc`
- `EXECUTIVE_SUMMARY.md` — `28f766810c046d46c385e4691dfd0c1502622cfb39e44f6bdce010b1c225bcbc`
- `BUG_REPORT.md` — `d83a7635cb8a14ec8d0545be885bcdd40600133981e606fb01edc53e7c591a32`
- `FUNCTIONAL_VALIDATION.md` — `636d6724f2037c39696b119bd93ba05fe32afae14d3568d9e15c471073a2ff82`
- `TEST_REPORT.md` — `e7b926681392595fd350c29607998d0001d7faadbce6ab4d3d66806cc90eeb8b`
- `DOCKER_VALIDATION.md` — `2abcd93a620b63f13c34116245661dc2d8b162d4342cb214411b4d44499124b0`
- `ML_VALIDATION.md` — `8157ab40f4bb8dcabb3a6529e64910f9939f117cb22588e36b369601958d8adc`
- `CHANGES.md` — `9e789f4731ca2dc66ce52c6c71d7adb00e3c3d810fb3ae4a79b90d11ebe3c454`
- `APPLY.md` — `4f7bba4e332d87dc28641de5cae61c81087af2df5173c6b62474fe123cc198a9`
- `TEST_RESULTS.txt` — `3592357234c7fa4f989aeafce873524bb724f9cd7f90c65632a457975472342c`
- `PATCH_MANIFEST.md` — `b05c4f2b716f9bf07efb4675205eb562b9f64384e86524ca663cd68872d98f68`
- `tests/audit/test_deployment_contract.py` — `5fd20aba78f4c388a9312df8abf49283bb9415c7d395f85c2018dfa04d3376ec`
- `tests/audit/test_grpc_validation.py` — `672c04957638b163d941ad6c0219879a9b05794a131f7966ff2b02346f688af9`
- `tests/audit/test_latest_feature_row.py` — `4cb888d78181bf26b1d836b0bccb4f11ffc30fb6c4a9a4c49a3e869a2f7cc23e`
- `tests/audit/test_market_closed_candles.py` — `4505f73445eb2f786aa50d3068f7e4cd8e6b8785795d7c8123ff805048b25bec`
- `tests/audit/test_model_metadata.py` — `af46c5f88999e38c9d177ff38390ccc8ef989ef4b1a6a47b0bcbd086a7d4882e`
- `tests/audit/test_model_predictor_reload.py` — `ffca786d67397f623554e96eb59aa61d3f123a5cf4aa23b0fa0a47f868e9e682`
- `tests/audit/test_risk_boundaries.py` — `2a5643bd2ac610a18d1af3d62b3719e3264cf69502d619121e7cd967a05d3af6`
- `tests/audit/test_storage_concurrency.py` — `48e2da24288331dfa869b5c2e7158a69af0a862a3bac7f73155aaf3c9e749751`
- `tests/audit/test_strategy_selection.py` — `24ddd610f3c6e47c2e94887e0e013fd817c80954d88f8c6598a4ea20e7282ba0`

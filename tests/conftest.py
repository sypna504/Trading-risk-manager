from __future__ import annotations

import os
import sys
import types
from pathlib import Path


os.environ.setdefault("DATABASE_PATH", str(Path(".test-data") / "test.db"))
os.environ.setdefault("ML_SERVICE_ADDRESS", "localhost:50051")
os.environ.setdefault(
    "MODEL_PATH",
    "app/ml_services/app/models/risk_model_v2_online.cbm",
)
os.environ.setdefault(
    "MODEL_CONFIG_PATH",
    "app/ml_services/app/models/risk_model_v2_online_config.json",
)

# Local contributor environments may run smoke tests before installing ccxt.
# Production and Docker still use the real package from requirements files.
try:
    import ccxt  # noqa: F401
except ImportError:
    ccxt_stub = types.ModuleType("ccxt")

    class _Exchange:
        rateLimit = 0

        def __init__(self, *_args, **_kwargs):
            pass

    ccxt_stub.binance = _Exchange
    ccxt_stub.bybit = _Exchange
    sys.modules["ccxt"] = ccxt_stub

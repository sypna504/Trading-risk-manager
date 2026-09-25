from __future__ import annotations

import importlib.util
import os

import pytest


required = ["ccxt", "grpc_health", "ml.v1.ml_pb2"]
missing = []
for name in required:
    try:
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    except (ModuleNotFoundError, ValueError):
        missing.append(name)
pytestmark = pytest.mark.skipif(
    bool(missing),
    reason="clean-install integration dependencies/generated proto unavailable: " + ", ".join(missing),
)


def test_backend_lifespan_health(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "trading_risk.db"))
    monkeypatch.setenv("OUTCOME_AUTO_EVALUATION", "false")
    from fastapi.testclient import TestClient
    from app.backend.api.app.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

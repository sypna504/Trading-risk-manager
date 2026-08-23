from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from app.config import DEFAULT_MODELS_ROOT, Settings


def test_settings_defaults_and_environment_aliases(monkeypatch, tmp_path):
    default = Settings(_env_file=None)
    assert default.ML_SERVICE_PORT == 50051
    assert default.MIN_CANDLES == 60
    assert default.MODELS_ROOT == DEFAULT_MODELS_ROOT

    monkeypatch.setenv("ML_MODELS_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("ML_REGISTRY_PATH", str(tmp_path / "registry.json"))
    configured = Settings(_env_file=None)
    assert configured.MODELS_ROOT == tmp_path / "models"
    assert configured.MODEL_REGISTRY_PATH == tmp_path / "registry.json"


def test_server_serv_starts_registers_and_waits(monkeypatch):
    fake_grpc = ModuleType("grpc")
    state = {"registered": False, "started": False, "waited": False}

    class FakeServer:
        def add_insecure_port(self, address):
            state["address"] = address

        def start(self):
            state["started"] = True

        def wait_for_termination(self):
            state["waited"] = True

    fake_grpc.server = lambda executor: FakeServer()
    monkeypatch.setitem(sys.modules, "grpc", fake_grpc)

    ml_module = ModuleType("ml")
    ml_v1_module = ModuleType("ml.v1")
    ml_pb2_grpc = ModuleType("ml.v1.ml_pb2_grpc")

    def register(service, server):
        state["registered"] = True
        state["service"] = service

    ml_pb2_grpc.add_MLServiceServicer_to_server = register
    monkeypatch.setitem(sys.modules, "ml", ml_module)
    monkeypatch.setitem(sys.modules, "ml.v1", ml_v1_module)
    monkeypatch.setitem(sys.modules, "ml.v1.ml_pb2_grpc", ml_pb2_grpc)

    fake_service = ModuleType("app.online.service")
    fake_service.MLService = type("MLService", (), {})
    monkeypatch.setitem(sys.modules, "app.online.service", fake_service)

    fake_inference = ModuleType("app.online.ml_inference")
    fake_inference.predictor = SimpleNamespace(
        metadata=lambda: {
            "model_version": "v1",
            "model_path": "model.cbm",
            "threshold": 0.5,
            "train_end": "2026-01-01",
            "loaded_at": "2026-01-02",
        }
    )
    monkeypatch.setitem(sys.modules, "app.online.ml_inference", fake_inference)

    sys.modules.pop("app.online.server", None)
    server_module = importlib.import_module("app.online.server")
    monkeypatch.setattr(
        server_module,
        "settings",
        SimpleNamespace(ML_SERVICE_PORT=50051, MODEL_VERSION="v1"),
    )
    server_module.serv()
    assert state["registered"] is True
    assert state["started"] is True
    assert state["waited"] is True
    assert state["address"] == "[::]:50051"

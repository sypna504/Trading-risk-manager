from pathlib import Path


def test_compose_persists_database_and_shares_model_registry():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "backend_data:/app/data" in compose
    assert "./app/ml_services/app/models:/app/app/ml_services/app/models:ro" in compose
    assert "MODEL_REGISTRY_PATH" in compose


def test_requirements_match_checked_in_generated_proto_versions():
    for path in (
        Path("app/backend/api/requirements.txt"),
        Path("app/ml_services/requirements.txt"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "grpcio>=1.81.1" in text
        assert "grpcio-tools>=1.81.1" in text
        assert "protobuf>=6.33.5" in text

from fastapi.testclient import TestClient

from app.backend.api.app.main import app
from app.backend.api.app.routers import health_router


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(health_router.health_client, "is_ready", lambda timeout: True)

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["backend"] == "available"

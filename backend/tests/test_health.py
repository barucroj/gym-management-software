"""Smoke tests de los endpoints de salud."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_db_ok() -> None:
    """Requiere el servicio db arriba (docker compose run --rm tests)."""
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["database"] == "reachable"

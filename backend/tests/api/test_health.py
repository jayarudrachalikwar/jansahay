from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_status_payload() -> None:
    response = client.get("/api/health")

    assert response.status_code in (200, 503)
    payload = response.json()
    assert "status" in payload
    assert "database" in payload
    assert payload["database"] in ("connected", "disconnected")

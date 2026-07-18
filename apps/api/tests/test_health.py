from fastapi.testclient import TestClient

from sic_api.main import app


client = TestClient(app)


def test_live_healthcheck() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"]


def test_ready_healthcheck() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

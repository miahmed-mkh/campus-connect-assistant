from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "Campus Connect Assistant API",
        "version": "1.0.0",
        "environment": "development",
    }

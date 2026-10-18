from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.core import console_auth
from backend.app.core.config import settings
from backend.app.main import app

client = TestClient(app)

SECRET = "secret-de-test-pour-la-console-iot"
DEVICE_KEY = "cle-appareil-de-test"
ANALYTICS_KEY = "cle-analytics-de-test"
OPERATORS = ["responsable", "intervenant"]


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(settings, "console_token_secret", SECRET)
    monkeypatch.setattr(settings, "iot_device_key", DEVICE_KEY)
    monkeypatch.setattr(settings, "analytics_api_key", ANALYTICS_KEY)


def bearer(role: str, secret: str = SECRET, now: float | None = None) -> dict:
    token = console_auth.create_token(
        role + ".test", role, secret, 3600, now=now
    )
    return {"Authorization": "Bearer " + token}


def payload() -> dict:
    return {
        "device_id": "sensor-manual-01",
        "readings": [
            {
                "kind": "temperature",
                "value": 21.5,
                "unit": "C",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }


def post_telemetry(headers: dict):
    return client.post("/api/iot/telemetry", json=payload(), headers=headers)


def get_status(headers: dict):
    return client.get("/api/iot/status", headers=headers)


@pytest.mark.parametrize("role", OPERATORS)
def test_telemetry_accepts_operator_token(role) -> None:
    assert post_telemetry(bearer(role)).status_code == 202


def test_telemetry_forbids_student_token() -> None:
    response = post_telemetry(bearer("etudiant"))

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "forbidden_role"


def test_telemetry_requires_credentials() -> None:
    assert post_telemetry({}).status_code == 401


def test_telemetry_rejects_token_signed_with_other_secret() -> None:
    response = post_telemetry(bearer("responsable", secret="autre-secret"))

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_token"


def test_telemetry_rejects_expired_token() -> None:
    assert post_telemetry(bearer("responsable", now=1000)).status_code == 401


def test_telemetry_rejects_non_bearer_scheme() -> None:
    response = post_telemetry({"Authorization": "Basic abc"})

    assert response.status_code == 401


def test_telemetry_still_accepts_device_key() -> None:
    response = post_telemetry({"X-Device-Key": DEVICE_KEY})

    assert response.status_code == 202


def test_student_token_is_not_overridden_by_a_valid_device_key() -> None:
    headers = {**bearer("etudiant"), "X-Device-Key": DEVICE_KEY}

    assert post_telemetry(headers).status_code == 403


@pytest.mark.parametrize("role", OPERATORS)
def test_status_accepts_operator_token(role) -> None:
    assert get_status(bearer(role)).status_code == 200


def test_status_forbids_student_token() -> None:
    response = get_status(bearer("etudiant"))

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "forbidden_role"


def test_status_requires_credentials() -> None:
    assert get_status({}).status_code == 401


def test_status_rejects_forged_token() -> None:
    response = get_status(bearer("responsable", secret="autre-secret"))

    assert response.status_code == 401


def test_status_still_accepts_analytics_key() -> None:
    assert get_status({"X-Analytics-Key": ANALYTICS_KEY}).status_code == 200


def test_console_token_does_not_open_analytics_summary() -> None:
    response = client.get(
        "/api/analytics/summary", headers=bearer("responsable")
    )

    assert response.status_code == 401

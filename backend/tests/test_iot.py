from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.core.config import settings
from backend.app.db.database import SessionLocal
from backend.app.main import app
from backend.app.models.iot_reading import IotReading

client = TestClient(app)

DEVICE_KEY = "test-device-key"
ANALYTICS_KEY = "test-analytics-key"
TELEMETRY_URL = "/api/iot/telemetry"
STATUS_URL = "/api/iot/status"


@pytest.fixture
def device_key(monkeypatch):
    monkeypatch.setattr(settings, "iot_device_key", DEVICE_KEY)
    return DEVICE_KEY


@pytest.fixture
def analytics_key(monkeypatch):
    monkeypatch.setattr(settings, "analytics_api_key", ANALYTICS_KEY)
    return ANALYTICS_KEY


def make_payload(device_id: str = "kiosk-hall-01", readings=None) -> dict:
    if readings is None:
        readings = [
            {
                "kind": "temperature",
                "value": 21.5,
                "unit": "C",
                "recorded_at": "2026-10-12T10:00:00Z",
            },
            {
                "kind": "occupancy",
                "value": 3,
                "unit": "persons",
                "recorded_at": "2026-10-12T10:00:00Z",
            },
        ]
    return {"device_id": device_id, "readings": readings}


def post_telemetry(payload: dict, key: str | None):
    headers = {"X-Device-Key": key} if key is not None else {}
    return client.post(TELEMETRY_URL, json=payload, headers=headers)


def count_readings() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count(IotReading.id))) or 0


# --- POST /api/iot/telemetry -------------------------------------------------


def test_telemetry_returns_503_when_key_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "iot_device_key", "")

    response = post_telemetry(make_payload(), key="anything")

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "iot_disabled"


def test_telemetry_returns_401_without_header(device_key) -> None:
    response = post_telemetry(make_payload(), key=None)

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_device_key"
    assert count_readings() == 0


def test_telemetry_returns_401_with_wrong_key(device_key) -> None:
    response = post_telemetry(make_payload(), key="wrong-key")

    assert response.status_code == 401
    assert count_readings() == 0


def test_telemetry_accepts_valid_payload(device_key) -> None:
    response = post_telemetry(make_payload(), key=device_key)

    assert response.status_code == 202
    body = response.json()
    assert body["device_id"] == "kiosk-hall-01"
    assert body["accepted"] == 2
    assert "received_at" in body
    assert count_readings() == 2


@pytest.mark.parametrize(
    "payload",
    [
        make_payload(device_id="Kiosk Hall 01"),
        make_payload(device_id=""),
        make_payload(readings=[]),
        make_payload(
            readings=[
                {
                    "kind": "pressure",
                    "value": 1.0,
                    "recorded_at": "2026-10-12T10:00:00Z",
                }
            ]
        ),
        make_payload(
            readings=[
                {"kind": "temperature", "value": "hot", "recorded_at": "2026-10-12T10:00:00Z"}
            ]
        ),
        make_payload(
            readings=[
                {
                    "kind": "heartbeat",
                    "value": 1,
                    "recorded_at": "2026-10-12T10:00:00Z",
                }
            ]
            * 51
        ),
    ],
    ids=[
        "device_id_uppercase_and_spaces",
        "device_id_empty",
        "readings_empty",
        "kind_unknown",
        "value_not_numeric",
        "too_many_readings",
    ],
)
def test_telemetry_rejects_invalid_payload(device_key, payload) -> None:
    response = post_telemetry(payload, key=device_key)

    assert response.status_code == 422
    assert count_readings() == 0


# --- GET /api/iot/status -----------------------------------------------------


def test_status_returns_401_without_analytics_key(analytics_key) -> None:
    response = client.get(STATUS_URL)

    assert response.status_code == 401


def test_status_is_empty_without_readings(analytics_key) -> None:
    response = client.get(STATUS_URL, headers={"X-Analytics-Key": analytics_key})

    assert response.status_code == 200
    body = response.json()
    assert body["readings_total"] == 0
    assert body["devices"] == []
    assert body["online_threshold_seconds"] == settings.iot_online_threshold_seconds


def test_status_reports_online_device_with_latest_readings(
    device_key, analytics_key
) -> None:
    post_telemetry(make_payload(), key=device_key)
    post_telemetry(
        make_payload(
            readings=[
                {
                    "kind": "temperature",
                    "value": 23.0,
                    "unit": "C",
                    "recorded_at": "2026-10-12T10:05:00Z",
                }
            ]
        ),
        key=device_key,
    )

    response = client.get(STATUS_URL, headers={"X-Analytics-Key": analytics_key})

    assert response.status_code == 200
    body = response.json()
    assert body["readings_total"] == 3
    assert len(body["devices"]) == 1

    device = body["devices"][0]
    assert device["device_id"] == "kiosk-hall-01"
    assert device["online"] is True

    latest = {item["kind"]: item["value"] for item in device["latest"]}
    assert latest == {"temperature": 23.0, "occupancy": 3.0}


def test_status_marks_stale_device_offline(analytics_key) -> None:
    stale_time = datetime.now(timezone.utc) - timedelta(
        seconds=settings.iot_online_threshold_seconds + 60
    )
    with SessionLocal() as db:
        db.add(
            IotReading(
                device_id="sensor-b204",
                kind="humidity",
                value=45.0,
                unit="%",
                recorded_at=stale_time,
                received_at=stale_time,
            )
        )
        db.commit()

    response = client.get(STATUS_URL, headers={"X-Analytics-Key": analytics_key})

    assert response.status_code == 200
    devices = response.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == "sensor-b204"
    assert devices[0]["online"] is False

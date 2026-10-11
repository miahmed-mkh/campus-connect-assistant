import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app

client = TestClient(app)
SUMMARY_URL = "/api/analytics/summary"
TEST_KEY = "cle-de-test-analytics"


@pytest.fixture
def analytics_key(monkeypatch):
    monkeypatch.setattr(settings, "analytics_api_key", TEST_KEY)
    return TEST_KEY


def test_returns_503_when_key_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "analytics_api_key", "")

    response = client.get(SUMMARY_URL, headers={"X-Analytics-Key": "x"})

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "analytics_disabled"


def test_returns_401_without_header(analytics_key) -> None:
    response = client.get(SUMMARY_URL)

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_analytics_key"


def test_returns_401_with_wrong_key(analytics_key) -> None:
    response = client.get(SUMMARY_URL, headers={"X-Analytics-Key": "mauvaise"})

    assert response.status_code == 401


def test_returns_empty_summary_with_valid_key(analytics_key) -> None:
    response = client.get(SUMMARY_URL, headers={"X-Analytics-Key": TEST_KEY})

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"]["days"] == 30
    assert payload["sessions"]["total"] == 0
    assert payload["messages"]["total"] == 0
    assert payload["feedback"]["satisfaction_rate"] == 0.0
    assert payload["daily"] == []


@pytest.mark.parametrize("days", (0, 366, "abc"))
def test_rejects_invalid_days(analytics_key, days) -> None:
    response = client.get(
        SUMMARY_URL,
        params={"days": days},
        headers={"X-Analytics-Key": TEST_KEY},
    )

    assert response.status_code == 422


def test_summary_reflects_chat_usage(analytics_key) -> None:
    session_id = str(uuid.uuid4())
    chat = client.post(
        "/api/chat",
        json={"message": "Bonjour", "session_id": session_id},
    )
    assert chat.status_code == 200

    response = client.get(
        SUMMARY_URL,
        params={"days": 1},
        headers={"X-Analytics-Key": TEST_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"]["days"] == 1
    assert payload["sessions"]["total"] == 1
    assert payload["messages"] == {"total": 2, "user": 1, "assistant": 1}
    assert payload["resolution"]["resolved"] + payload["resolution"]["unresolved"] == 1
    assert len(payload["daily"]) == 1
    assert payload["daily"][0]["messages"] == 2

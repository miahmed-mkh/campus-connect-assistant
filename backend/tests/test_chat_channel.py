import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.database import SessionLocal
from backend.app.main import app
from backend.app.models.session import ConversationSession

client = TestClient(app)

ANALYTICS_KEY = "test-analytics-key"


@pytest.fixture
def analytics_key(monkeypatch):
    monkeypatch.setattr(settings, "analytics_api_key", ANALYTICS_KEY)
    return ANALYTICS_KEY


def send_chat(session_id: str, channel: str | None = None):
    body = {"session_id": session_id, "message": "Bonjour"}
    if channel is not None:
        body["channel"] = channel
    return client.post("/api/chat", json=body)


def get_channel(session_id: str) -> str:
    with SessionLocal() as db:
        conversation = db.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id == session_id
            )
        )
        assert conversation is not None
        return conversation.channel


def test_chat_defaults_to_web_channel() -> None:
    session_id = str(uuid.uuid4())

    response = send_chat(session_id)

    assert response.status_code == 200
    assert get_channel(session_id) == "web"


def test_chat_persists_kiosk_channel() -> None:
    session_id = str(uuid.uuid4())

    response = send_chat(session_id, channel="kiosk")

    assert response.status_code == 200
    assert get_channel(session_id) == "kiosk"


def test_chat_keeps_original_channel_on_following_messages() -> None:
    session_id = str(uuid.uuid4())

    send_chat(session_id, channel="kiosk")
    send_chat(session_id, channel="web")

    assert get_channel(session_id) == "kiosk"


def test_chat_rejects_unknown_channel() -> None:
    response = send_chat(str(uuid.uuid4()), channel="sms")

    assert response.status_code == 422


def test_analytics_breaks_down_sessions_by_channel(analytics_key) -> None:
    send_chat(str(uuid.uuid4()), channel="kiosk")
    send_chat(str(uuid.uuid4()), channel="kiosk")
    send_chat(str(uuid.uuid4()))

    response = client.get(
        "/api/analytics/summary",
        headers={"X-Analytics-Key": analytics_key},
    )

    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert sessions["total"] == 3
    assert sessions["by_channel"] == [
        {"channel": "kiosk", "count": 2},
        {"channel": "web", "count": 1},
    ]

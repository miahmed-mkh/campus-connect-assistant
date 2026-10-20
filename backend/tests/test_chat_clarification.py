import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db.database import SessionLocal
from backend.app.main import app
from backend.app.models import Message
from backend.app.services.rate_limit_service import reset_rate_limit

client = TestClient(app)

chat_module = sys.modules["backend.app.api.chat"]

SESSION_ID = "test-chat-clarification"
SUGGESTIONS = [
    "Comment obtenir une convention de stage ?",
    "Comment choisir entre stage et alternance ?",
]


def fake_clarification(question: str, language: str = "fr") -> dict:
    return {
        "answer": "Je ne suis pas sûr d’avoir bien compris. Vouliez-vous dire :",
        "source": None,
        "category": "clarification",
        "confidence": 0.669,
        "suggestions": SUGGESTIONS,
    }


@pytest.fixture(autouse=True)
def reset_limits() -> None:
    reset_rate_limit(SESSION_ID)
    yield
    reset_rate_limit(SESSION_ID)


def test_clarification_returns_suggestions_and_is_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rephrase_calls = []

    monkeypatch.setattr(chat_module, "search_knowledge", fake_clarification)
    monkeypatch.setattr(
        chat_module,
        "rephrase_answer",
        lambda question, passage: rephrase_calls.append(question),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "je veux faire un stage, je fais comment ?",
            "session_id": SESSION_ID,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "clarification"
    assert data["resolved"] is False
    assert data["suggestions"] == SUGGESTIONS

    # Le LLM ne reformule pas une demande de clarification
    assert rephrase_calls == []

    database = SessionLocal()
    try:
        stored = database.scalars(
            select(Message).where(Message.role == "assistant")
        ).all()
    finally:
        database.close()

    assert [message.resolved for message in stored] == [False]
    assert [message.category for message in stored] == ["clarification"]


def test_regular_answer_has_no_suggestions() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Bonjour", "session_id": SESSION_ID},
    )

    assert response.status_code == 200
    assert response.json()["suggestions"] == []

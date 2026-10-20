import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db.database import SessionLocal
from backend.app.main import app
from backend.app.models import ConversationSession
from backend.app.services.rate_limit_service import reset_rate_limit
from backend.app.services.translation_service import (
    ENGLISH_FIXED_ANSWERS,
    MACHINE_TRANSLATION_NOTE,
)

client = TestClient(app)

chat_module = sys.modules["backend.app.api.chat"]

SESSION_ID = "test-chat-english"

FRENCH_SCHOOL_HOURS = (
    "Le service scolarité est ouvert du lundi au vendredi, de 9h à 17h."
)


@pytest.fixture(autouse=True)
def reset_limits() -> None:
    reset_rate_limit(SESSION_ID)
    yield
    reset_rate_limit(SESSION_ID)


def ask(message: str) -> dict:
    response = client.post(
        "/api/chat",
        json={"message": message, "session_id": SESSION_ID},
    )
    assert response.status_code == 200
    return response.json()


def test_english_question_gets_english_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rephrase_calls = []
    monkeypatch.setattr(
        chat_module,
        "rephrase_answer",
        lambda question, passage: rephrase_calls.append(question),
    )

    monkeypatch.setattr(
        chat_module,
        "search_knowledge",
        lambda question, language="fr": {
            "answer": FRENCH_SCHOOL_HOURS,
            "source": "Guide de l'étudiant",
            "category": "service_campus",
            "confidence": 0.9,
        },
    )

    data = ask("What are the opening hours of the student office?")

    assert data["language"] == "en"
    assert data["answer"].endswith(MACHINE_TRANSLATION_NOTE)
    assert "9h à 17h" not in data["answer"]
    # Le LLM reformule en français : il n'est pas appelé en anglais
    assert rephrase_calls == []

    database = SessionLocal()
    try:
        session = database.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id == SESSION_ID
            )
        )
    finally:
        database.close()

    assert session.language == "en"


def test_english_clarification_translates_message_and_suggestions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "search_knowledge",
        lambda question, language="fr": {
            "answer": "Je ne suis pas sûr d’avoir bien compris.",
            "source": None,
            "category": "clarification",
            "confidence": 0.62,
            "suggestions": ["Quels sont les horaires de la scolarité ?"],
        },
    )

    data = ask("how do I do my request")

    assert data["answer"] == ENGLISH_FIXED_ANSWERS["clarification"]
    assert data["suggestions"] != ["Quels sont les horaires de la scolarité ?"]
    assert len(data["suggestions"]) == 1


def test_english_unknown_question_gets_english_fallback() -> None:
    data = ask("How do I book a helicopter on campus?")

    assert data["language"] == "en"
    assert data["resolved"] is False
    assert data["answer"] == ENGLISH_FIXED_ANSWERS["unknown"]


def test_french_question_is_unchanged() -> None:
    data = ask("Quels sont les horaires de la scolarité ?")

    assert data["language"] == "fr"
    assert data["answer"] == FRENCH_SCHOOL_HOURS

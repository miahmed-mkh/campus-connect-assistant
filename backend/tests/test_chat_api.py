from sqlalchemy import select
from backend.app.db.database import SessionLocal
from backend.app.models import ConversationSession, Message
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app


client = TestClient(app)

LOGGING_TEST_USER_ID = "test-chat-api-logging"
PII_TEST_USER_ID = "test-chat-api-pii"

def cleanup_logging_test_data() -> None:
    database = SessionLocal()

    try:
        conversations = database.scalars(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == LOGGING_TEST_USER_ID
            )
        ).all()

        for conversation in conversations:
            database.delete(conversation)

        database.commit()

    finally:
        database.close()

def cleanup_chat_test_data() -> None:
    database = SessionLocal()

    try:
        conversations = database.scalars(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id.in_(
                    [
                        "session-001",
                        LOGGING_TEST_USER_ID,
                        PII_TEST_USER_ID,
                    ]
                )
            )
        ).all()

        for conversation in conversations:
            database.delete(conversation)

        database.commit()

    finally:
        database.close()

@pytest.fixture(autouse=True)
def clean_chat_test_data() -> None:
    cleanup_chat_test_data()

    yield

    cleanup_chat_test_data()

def test_chat_with_known_question() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "À quelle heure est ouverte la scolarité ?",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "Le service scolarité est ouvert du lundi au vendredi, "
            "de 9h à 17h."
        ),
        "source": "Guide de l'étudiant",
        "category": "service_campus",
        "confidence": 0.917,
        "resolved": True,
    }


def test_chat_with_greeting() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "Bonjour",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "Bonjour ! Posez-moi votre question sur le campus, "
            "je suis là pour vous aider."
        ),
        "source": None,
        "category": "salutation",
        "confidence": 1.0,
        "resolved": True,
    }



def test_chat_with_unknown_question() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "Comment réserver un hélicoptère sur le campus ?",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["source"] is None
    assert data["category"] == "unknown"
    assert data["confidence"] < 0.65
    assert data["resolved"] is False
    assert "pas encore de réponse fiable" in data["answer"]


def test_chat_rejects_empty_message() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 422


def test_chat_rejects_missing_session_id() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "Bonjour",
        },
    )

    assert response.status_code == 422

def test_chat_logs_conversation_and_messages() -> None:
    cleanup_logging_test_data()

    try:
        response = client.post(
            "/api/chat",
            json={
                "message": "Bonjour",
                "session_id": LOGGING_TEST_USER_ID,
            },
        )

        assert response.status_code == 200

        database = SessionLocal()

        try:
            conversation = database.scalar(
                select(ConversationSession).where(
                    ConversationSession.anonymous_user_id
                    == LOGGING_TEST_USER_ID
                )
            )

            assert conversation is not None
            assert conversation.channel == "web"
            assert conversation.language == "fr"

            messages = database.scalars(
                select(Message)
                .where(
                    Message.session_id == conversation.id
                )
                .order_by(Message.created_at)
            ).all()

            assert len(messages) == 2

            user_message = messages[0]
            assistant_message = messages[1]

            assert user_message.role == "user"
            assert user_message.content_redacted == "Bonjour"
            assert user_message.response_time_ms is None
            assert user_message.category is None
            assert user_message.confidence is None
            assert user_message.source is None
            assert user_message.resolved is None

            assert assistant_message.role == "assistant"
            assert (
                assistant_message.category
                == "salutation"
            )
            assert assistant_message.confidence == 1.0
            assert assistant_message.source is None
            assert assistant_message.resolved is True
            assert assistant_message.response_time_ms >= 1

        finally:
            database.close()

    finally:
        cleanup_logging_test_data()

def test_chat_redacts_personal_data_before_storage() -> None:
    original_message = (
        "Bonjour, mon email est student@example.com, "
        "mon téléphone est 06 12 34 56 78 et "
        "mon IP est 192.168.1.42"
    )

    response = client.post(
        "/api/chat",
        json={
            "message": original_message,
            "session_id": PII_TEST_USER_ID,
        },
    )

    assert response.status_code == 200

    database = SessionLocal()

    try:
        conversation = database.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == PII_TEST_USER_ID
            )
        )

        assert conversation is not None

        user_message = database.scalar(
            select(Message).where(
                Message.session_id == conversation.id,
                Message.role == "user",
            )
        )

        assert user_message is not None
        assert user_message.content_redacted == (
            "Bonjour, mon email est [EMAIL], "
            "mon téléphone est [TELEPHONE] et "
            "mon IP est [IP]"
        )

        assert (
            "student@example.com"
            not in user_message.content_redacted
        )
        assert (
            "06 12 34 56 78"
            not in user_message.content_redacted
        )
        assert (
            "192.168.1.42"
            not in user_message.content_redacted
        )

    finally:
        database.close()

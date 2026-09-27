from sqlalchemy import select
from backend.app.db.database import SessionLocal
from backend.app.models import ConversationSession, Message
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.services.input_security_service import (
    MAX_MESSAGE_LENGTH,
)
from backend.app.services.rate_limit_service import (
    RATE_LIMIT_REQUESTS,
    reset_rate_limit,
)


client = TestClient(app)

LOGGING_TEST_USER_ID = "test-chat-api-logging"
PII_TEST_USER_ID = "test-chat-api-pii"
SECURITY_TEST_USER_ID = "test-chat-api-security"
RATE_LIMIT_TEST_USER_ID = "test-chat-api-rate-limit"

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
                        SECURITY_TEST_USER_ID,
                        RATE_LIMIT_TEST_USER_ID,
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
    reset_rate_limit()

    yield

    reset_rate_limit()
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

def test_chat_rejects_unsafe_input_without_persistence() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "<script>alert(1)</script>",
            "session_id": SECURITY_TEST_USER_ID,
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "unsafe_input",
            "reason": "script_tag",
            "message": (
                "Le message contient une entrée non autorisée."
            ),
        }
    }

    database = SessionLocal()

    try:
        conversation = database.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == SECURITY_TEST_USER_ID
            )
        )

        assert conversation is None

    finally:
        database.close()

def test_chat_rejects_message_above_maximum_length() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "a" * (MAX_MESSAGE_LENGTH + 1),
            "session_id": SECURITY_TEST_USER_ID,
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "unsafe_input",
            "reason": "message_too_long",
            "message": (
                "Le message contient une entrée non autorisée."
            ),
        }
    }

    database = SessionLocal()

    try:
        conversation = database.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == SECURITY_TEST_USER_ID
            )
        )

        assert conversation is None

    finally:
        database.close()

def test_chat_rejects_eleventh_request_without_persistence() -> None:
    responses = [
        client.post(
            "/api/chat",
            json={
                "message": "Bonjour",
                "session_id": RATE_LIMIT_TEST_USER_ID,
            },
        )
        for _ in range(RATE_LIMIT_REQUESTS + 1)
    ]

    assert all(
        response.status_code == 200
        for response in responses[:RATE_LIMIT_REQUESTS]
    )

    blocked_response = responses[-1]

    assert blocked_response.status_code == 429
    assert blocked_response.headers["Retry-After"] == "60"
    assert blocked_response.json() == {
        "detail": {
            "code": "rate_limit_exceeded",
            "limit": RATE_LIMIT_REQUESTS,
            "retry_after_seconds": 60,
            "message": (
                "Trop de requêtes. "
                "Veuillez patienter avant de réessayer."
            ),
        }
    }

    database = SessionLocal()

    try:
        conversation = database.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == RATE_LIMIT_TEST_USER_ID
            )
        )

        assert conversation is not None

        messages = database.scalars(
            select(Message).where(
                Message.session_id == conversation.id
            )
        ).all()

        assert len(messages) == RATE_LIMIT_REQUESTS * 2

    finally:
        database.close()

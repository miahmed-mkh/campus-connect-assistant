import pytest
from pydantic import ValidationError

from backend.app.schemas.chat import ChatRequest, ChatResponse


def test_valid_chat_request() -> None:
    request = ChatRequest(
        message="Quand ouvre la bibliothèque ?",
        session_id="session-001",
    )

    assert request.message == "Quand ouvre la bibliothèque ?"
    assert request.session_id == "session-001"


def test_empty_message_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            message="",
            session_id="session-001",
        )


def test_empty_session_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            message="Quand ouvre la bibliothèque ?",
            session_id="",
        )


def test_chat_response_with_source() -> None:
    response = ChatResponse(
        answer="La bibliothèque ouvre à 8h.",
        source="Guide étudiant",
        category="service_campus",
        confidence=0.92,
        resolved=True,
    )

    assert response.model_dump() == {
        "answer": "La bibliothèque ouvre à 8h.",
        "source": "Guide étudiant",
        "category": "service_campus",
        "confidence": 0.92,
        "resolved": True,
    }


def test_chat_response_without_source() -> None:
    response = ChatResponse(
        answer="Bonjour ! Comment puis-je vous aider ?",
        category="salutation",
        confidence=1.0,
        resolved=True,
    )

    assert response.model_dump() == {
        "answer": "Bonjour ! Comment puis-je vous aider ?",
        "source": None,
        "category": "salutation",
        "confidence": 1.0,
        "resolved": True,
    }


def test_chat_response_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        ChatResponse(
            answer="Réponse invalide",
            source=None,
            category="unknown",
            confidence=1.5,
            resolved=False,
        )

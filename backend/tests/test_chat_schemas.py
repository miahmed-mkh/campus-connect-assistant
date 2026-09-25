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
    )

    assert response.model_dump() == {
        "answer": "La bibliothèque ouvre à 8h.",
        "source": "Guide étudiant",
    }


def test_chat_response_without_source() -> None:
    response = ChatResponse(
        answer="Bonjour ! Comment puis-je vous aider ?",
    )

    assert response.model_dump() == {
        "answer": "Bonjour ! Comment puis-je vous aider ?",
        "source": None,
    }

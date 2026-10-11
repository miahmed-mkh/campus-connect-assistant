import uuid

from backend.app.models.message import Message
from backend.app.models.session import ConversationSession


def test_message_table_name() -> None:
    assert Message.__tablename__ == "messages"


def test_message_columns() -> None:
    expected_columns = {
        "id",
        "session_id",
        "role",
        "content_redacted",
        "created_at",
        "response_time_ms",
        "category",
        "confidence",
        "source",
        "resolved",
    }

    actual_columns = set(
        Message.__table__.columns.keys()
    )

    assert actual_columns == expected_columns


def test_message_foreign_key() -> None:
    foreign_keys = list(
        Message.__table__.c.session_id.foreign_keys
    )

    assert len(foreign_keys) == 1
    assert (
        foreign_keys[0].target_fullname
        == "conversation_sessions.id"
    )
    assert foreign_keys[0].ondelete == "CASCADE"


def test_user_message_creation() -> None:
    session_id = uuid.uuid4()

    message = Message(
        session_id=session_id,
        role="user",
        content_redacted="Quand ouvre la bibliothèque ?",
    )

    assert message.session_id == session_id
    assert message.role == "user"
    assert (
        message.content_redacted
        == "Quand ouvre la bibliothèque ?"
    )
    assert message.response_time_ms is None
    assert message.category is None
    assert message.confidence is None
    assert message.source is None
    assert message.resolved is None


def test_assistant_message_creation() -> None:
    session_id = uuid.uuid4()

    message = Message(
        session_id=session_id,
        role="assistant",
        content_redacted=(
            "La bibliothèque ouvre à 8h."
        ),
        response_time_ms=125,
        category="service_campus",
        confidence=0.94,
        source="Guide de l'étudiant",
        resolved=True,
    )

    assert message.session_id == session_id
    assert message.role == "assistant"
    assert message.response_time_ms == 125
    assert message.category == "service_campus"
    assert message.confidence == 0.94
    assert message.source == "Guide de l'étudiant"
    assert message.resolved is True

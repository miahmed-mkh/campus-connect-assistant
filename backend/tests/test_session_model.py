import uuid
from datetime import datetime

from backend.app.models.session import ConversationSession


def test_conversation_session_table_name() -> None:
    assert ConversationSession.__tablename__ == "conversation_sessions"


def test_conversation_session_columns() -> None:
    expected_columns = {
        "id",
        "anonymous_user_id",
        "channel",
        "language",
        "started_at",
        "ended_at",
    }

    actual_columns = set(
        ConversationSession.__table__.columns.keys()
    )

    assert actual_columns == expected_columns


def test_conversation_session_default_values() -> None:
    session = ConversationSession(
        anonymous_user_id="anonymous-user-001",
    )

    assert session.anonymous_user_id == "anonymous-user-001"
    assert session.ended_at is None


def test_conversation_session_accepts_uuid() -> None:
    session_id = uuid.uuid4()

    session = ConversationSession(
        id=session_id,
        anonymous_user_id="anonymous-user-001",
    )

    assert session.id == session_id


def test_conversation_session_accepts_end_date() -> None:
    end_date = datetime.now()

    session = ConversationSession(
        anonymous_user_id="anonymous-user-001",
        ended_at=end_date,
    )

    assert session.ended_at == end_date

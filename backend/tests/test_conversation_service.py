from sqlalchemy import func, select

from backend.app.api.chat import get_or_create_conversation
from backend.app.db.database import SessionLocal
from backend.app.models import ConversationSession
from backend.app.api.chat import (
    get_or_create_conversation,
    save_message,
)
from backend.app.models import ConversationSession, Message


TEST_USER_ID = "test-get-or-create-user"


def cleanup_test_sessions() -> None:
    database = SessionLocal()

    try:
        conversations = database.scalars(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == TEST_USER_ID
            )
        ).all()

        for conversation in conversations:
            database.delete(conversation)

        database.commit()

    finally:
        database.close()


def test_create_conversation_from_anonymous_id() -> None:
    cleanup_test_sessions()
    database = SessionLocal()

    try:
        conversation = get_or_create_conversation(
            database=database,
            session_id=TEST_USER_ID,
        )
        database.commit()
        database.refresh(conversation)

        assert conversation.id is not None
        assert conversation.anonymous_user_id == TEST_USER_ID
        assert conversation.channel == "web"
        assert conversation.language == "fr"

        conversation_count = database.scalar(
            select(func.count(ConversationSession.id)).where(
                ConversationSession.anonymous_user_id
                == TEST_USER_ID
            )
        )

        assert conversation_count == 1

    finally:
        database.close()
        cleanup_test_sessions()


def test_reuse_conversation_from_uuid() -> None:
    cleanup_test_sessions()
    database = SessionLocal()

    try:
        created_conversation = get_or_create_conversation(
            database=database,
            session_id=TEST_USER_ID,
        )
        database.commit()
        database.refresh(created_conversation)

        original_id = created_conversation.id

        reused_conversation = get_or_create_conversation(
            database=database,
            session_id=str(original_id),
        )
        database.commit()

        assert reused_conversation.id == original_id
        assert reused_conversation.anonymous_user_id == TEST_USER_ID

        conversation_count = database.scalar(
            select(func.count(ConversationSession.id)).where(
                ConversationSession.anonymous_user_id
                == TEST_USER_ID
            )
        )

        assert conversation_count == 1

    finally:
        database.close()
        cleanup_test_sessions()

def test_save_user_message() -> None:
    cleanup_test_sessions()
    database = SessionLocal()

    try:
        conversation = get_or_create_conversation(
            database=database,
            session_id=TEST_USER_ID,
        )

        message = save_message(
            database=database,
            conversation=conversation,
            role="user",
            content="Quand ouvre la bibliothèque ?",
        )

        database.commit()
        database.refresh(message)

        assert message.id is not None
        assert message.session_id == conversation.id
        assert message.role == "user"
        assert (
            message.content_redacted
            == "Quand ouvre la bibliothèque ?"
        )
        assert message.created_at is not None
        assert message.response_time_ms is None
        assert message.category is None
        assert message.confidence is None
        assert message.source is None
        assert message.resolved is None

    finally:
        database.close()
        cleanup_test_sessions()


def test_save_assistant_message() -> None:
    cleanup_test_sessions()
    database = SessionLocal()

    try:
        conversation = get_or_create_conversation(
            database=database,
            session_id=TEST_USER_ID,
        )

        message = save_message(
            database=database,
            conversation=conversation,
            role="assistant",
            content="La bibliothèque ouvre à 8h.",
            response_time_ms=125,
            category="service_campus",
            confidence=0.94,
            source="Guide de l'étudiant",
            resolved=True,
        )

        database.commit()
        database.refresh(message)

        assert message.id is not None
        assert message.session_id == conversation.id
        assert message.role == "assistant"
        assert message.response_time_ms == 125
        assert message.category == "service_campus"
        assert message.confidence == 0.94
        assert message.source == "Guide de l'étudiant"
        assert message.resolved is True

    finally:
        database.close()
        cleanup_test_sessions()

def test_reuse_conversation_from_anonymous_id() -> None:
    cleanup_test_sessions()
    database = SessionLocal()

    try:
        first_conversation = get_or_create_conversation(
            database=database,
            session_id=TEST_USER_ID,
        )
        database.commit()
        database.refresh(first_conversation)

        original_id = first_conversation.id

        second_conversation = get_or_create_conversation(
            database=database,
            session_id=TEST_USER_ID,
        )
        database.commit()

        assert second_conversation.id == original_id
        assert (
            second_conversation.anonymous_user_id
            == TEST_USER_ID
        )

        conversation_count = database.scalar(
            select(func.count(ConversationSession.id)).where(
                ConversationSession.anonymous_user_id
                == TEST_USER_ID
            )
        )

        assert conversation_count == 1

    finally:
        database.close()
        cleanup_test_sessions()

def test_save_message_redacts_personal_data() -> None:
    cleanup_test_sessions()
    database = SessionLocal()

    try:
        conversation = get_or_create_conversation(
            database=database,
            session_id=TEST_USER_ID,
        )

        message = save_message(
            database=database,
            conversation=conversation,
            role="user",
            content=(
                "Mon email est student@example.com, "
                "mon téléphone est 06 12 34 56 78, "
                "mon IP est 192.168.1.42 et "
                "mon numéro étudiant : ESIC-123456"
            ),
        )

        database.commit()
        database.refresh(message)

        assert message.content_redacted == (
            "Mon email est [EMAIL], "
            "mon téléphone est [TELEPHONE], "
            "mon IP est [IP] et "
            "mon [IDENTIFIANT_ETUDIANT]"
        )

        assert "student@example.com" not in message.content_redacted
        assert "06 12 34 56 78" not in message.content_redacted
        assert "192.168.1.42" not in message.content_redacted
        assert "ESIC-123456" not in message.content_redacted

    finally:
        database.close()
        cleanup_test_sessions()

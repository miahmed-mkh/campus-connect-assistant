from sqlalchemy import func, select

from backend.app.db.database import SessionLocal
from backend.app.models import ConversationSession, Message


def test_conversation_and_messages_persistence() -> None:
    database = SessionLocal()

    try:
        conversation = ConversationSession(
            anonymous_user_id="test-user-persistence",
            channel="web",
            language="fr",
        )

        database.add(conversation)
        database.flush()

        assert conversation.id is not None
        assert conversation.started_at is not None

        user_message = Message(
            session_id=conversation.id,
            role="user",
            content_redacted="Quand ouvre la bibliothèque ?",
        )

        assistant_message = Message(
            session_id=conversation.id,
            role="assistant",
            content_redacted="La bibliothèque ouvre à 8h.",
            response_time_ms=120,
            category="service_campus",
            confidence=0.95,
            source="Guide de l'étudiant",
            resolved=True,
        )

        database.add_all(
            [
                user_message,
                assistant_message,
            ]
        )
        database.commit()

        message_count = database.scalar(
            select(func.count(Message.id)).where(
                Message.session_id == conversation.id
            )
        )

        assert message_count == 2

        saved_messages = database.scalars(
            select(Message)
            .where(Message.session_id == conversation.id)
            .order_by(Message.created_at)
        ).all()

        assert saved_messages[0].role == "user"
        assert saved_messages[1].role == "assistant"
        assert saved_messages[1].resolved is True

    finally:
        database.rollback()

        conversation = database.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == "test-user-persistence"
            )
        )

        if conversation is not None:
            database.delete(conversation)
            database.commit()

        database.close()

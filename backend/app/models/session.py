import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    anonymous_user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="web",
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="fr",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

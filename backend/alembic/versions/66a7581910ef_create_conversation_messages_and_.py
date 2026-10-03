"""Create conversation, message and feedback tables.

Revision ID: 66a7581910ef
Revises:
Create Date: 2026-10-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "66a7581910ef"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "anonymous_user_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_conversation_sessions_anonymous_user_id",
        "conversation_sessions",
        ["anonymous_user_id"],
        unique=False,
    )

    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "content_redacted",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "response_time_ms",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "resolved",
            sa.Boolean(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["conversation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_messages_session_id",
        "messages",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "feedbacks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "rating",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rating IN ('up', 'down')",
            name="ck_feedbacks_rating",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_feedbacks_message_id",
        "feedbacks",
        ["message_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_feedbacks_message_id",
        table_name="feedbacks",
    )
    op.drop_table("feedbacks")

    op.drop_index(
        "ix_messages_session_id",
        table_name="messages",
    )
    op.drop_table("messages")

    op.drop_index(
        "ix_conversation_sessions_anonymous_user_id",
        table_name="conversation_sessions",
    )
    op.drop_table("conversation_sessions")
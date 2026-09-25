from uuid import UUID
from backend.app.models import ConversationSession, Message
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from time import perf_counter
from sqlalchemy import select

from backend.app.db.database import get_db
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.knowledge_service import knowledge_service


router = APIRouter(
    prefix="/api",
    tags=["Chat"],
)


def get_or_create_conversation(
    database: Session,
    session_id: str,
) -> ConversationSession:
    conversation = None

    try:
        conversation_uuid = UUID(session_id)
    except ValueError:
        conversation_uuid = None

    if conversation_uuid is not None:
        conversation = database.get(
            ConversationSession,
            conversation_uuid,
        )

    if conversation is None:
        conversation = database.scalar(
            select(ConversationSession)
            .where(
                ConversationSession.anonymous_user_id
                == session_id
            )
            .order_by(
                ConversationSession.started_at.desc()
            )
            .limit(1)
        )

    if conversation is not None:
        return conversation

    conversation = ConversationSession(
        anonymous_user_id=session_id,
        channel="web",
        language="fr",
    )

    database.add(conversation)
    database.flush()

    return conversation

def save_message(
    database: Session,
    conversation: ConversationSession,
    role: str,
    content: str,
    response_time_ms: int | None = None,
    category: str | None = None,
    confidence: float | None = None,
    source: str | None = None,
    resolved: bool | None = None,
) -> Message:
    message = Message(
        session_id=conversation.id,
        role=role,
        content_redacted=content,
        response_time_ms=response_time_ms,
        category=category,
        confidence=confidence,
        source=source,
        resolved=resolved,
    )

    database.add(message)
    database.flush()

    return message


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    database: Session = Depends(get_db),
) -> ChatResponse:
    started_at = perf_counter()

    try:
        conversation = get_or_create_conversation(
            database=database,
            session_id=request.session_id,
        )

        save_message(
            database=database,
            conversation=conversation,
            role="user",
            content=request.message,
        )

        result = knowledge_service.search(request.message)
        resolved = result["category"] != "unknown"

        response_time_ms = max(
            1,
            round(
                (perf_counter() - started_at) * 1000
            ),
        )

        save_message(
            database=database,
            conversation=conversation,
            role="assistant",
            content=result["answer"],
            response_time_ms=response_time_ms,
            category=result["category"],
            confidence=result["confidence"],
            source=result["source"],
            resolved=resolved,
        )

        database.commit()

    except Exception:
        database.rollback()
        raise

    return ChatResponse(
        answer=result["answer"],
        source=result["source"],
        category=result["category"],
        confidence=result["confidence"],
        resolved=resolved,
    )

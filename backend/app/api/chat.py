from uuid import UUID
from backend.app.models import ConversationSession, Message
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session
from time import perf_counter
from sqlalchemy import select

from backend.app.db.database import get_db
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.core.exceptions import (
    RateLimitExceededError,
    UnsafeInputError,
)
from backend.app.services.input_security_service import (
    validate_user_input,
)

from backend.app.services.rate_limit_service import (
    check_rate_limit,
)

from backend.app.services.knowledge_service import (
    search_knowledge,
)

from backend.app.services.pii_redaction_service import (
    redact_personal_data,
)


router = APIRouter(
    prefix="/api",
    tags=["Chat"],
)


def get_or_create_conversation(
    database: Session,
    session_id: str,
    channel: str = "web",
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
        channel=channel,
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
        content_redacted=redact_personal_data(content),
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
        security_result = validate_user_input(
            request.message
        )

        if not security_result.is_safe:
            raise UnsafeInputError(
                security_result.reason or "unsafe_input"
            )

        safe_message = security_result.sanitized_text

        rate_limit_result = check_rate_limit(
            request.session_id
        )

        if not rate_limit_result.allowed:
            raise RateLimitExceededError(
                limit=rate_limit_result.limit,
                retry_after_seconds=(
                    rate_limit_result.retry_after_seconds
                ),
            )

        conversation = get_or_create_conversation(
            database=database,
            session_id=request.session_id,
            channel=request.channel,
        )

        save_message(
            database=database,
            conversation=conversation,
            role="user",
            content=safe_message,
        )

        result = search_knowledge(safe_message)
        resolved = result["category"] != "unknown"

        response_time_ms = max(
            1,
            round(
                (perf_counter() - started_at) * 1000
            ),
        )

        assistant_message = save_message(
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

    except RateLimitExceededError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limit_exceeded",
                "limit": error.limit,
                "retry_after_seconds": (
                    error.retry_after_seconds
                ),
                "message": (
                    "Trop de requêtes. "
                    "Veuillez patienter avant de réessayer."
                ),
            },
            headers={
                "Retry-After": str(
                    error.retry_after_seconds
                ),
            },
        ) from error


    except UnsafeInputError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "unsafe_input",
                "reason": error.reason,
                "message": (
                    "Le message contient une entrée non autorisée."
                ),
            },
        ) from error

    except Exception:
        database.rollback()
        raise

    return ChatResponse(
        message_id=assistant_message.id,
        answer=result["answer"],
        source=result["source"],
        category=result["category"],
        confidence=result["confidence"],
        resolved=resolved,
    )

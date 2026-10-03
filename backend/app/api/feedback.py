from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.models import ConversationSession, Feedback, Message
from backend.app.schemas.feedback import (
    FeedbackRequest,
    FeedbackResponse,
)


router = APIRouter(
    prefix="/api",
    tags=["Feedback"],
)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
)
def save_feedback(
    request: FeedbackRequest,
    database: Session = Depends(get_db),
) -> FeedbackResponse:
    try:
        message = database.scalar(
            select(Message)
            .join(
                ConversationSession,
                ConversationSession.id == Message.session_id,
            )
            .where(
                Message.id == request.message_id,
                Message.role == "assistant",
                ConversationSession.anonymous_user_id
                == request.session_id,
            )
        )

        if message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "message_not_found",
                    "message": (
                        "Le message assistant est introuvable "
                        "pour cette session."
                    ),
                },
            )

        feedback = database.scalar(
            select(Feedback).where(
                Feedback.message_id == message.id
            )
        )

        if feedback is None:
            feedback = Feedback(
                message_id=message.id,
                rating=request.rating,
            )
            database.add(feedback)
        else:
            feedback.rating = request.rating

        database.commit()
        database.refresh(feedback)

    except HTTPException:
        database.rollback()
        raise

    except Exception:
        database.rollback()
        raise

    return FeedbackResponse(
        message_id=feedback.message_id,
        rating=feedback.rating,
        status="saved",
    )

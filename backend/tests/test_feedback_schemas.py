from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.schemas.feedback import (
    FeedbackRequest,
    FeedbackResponse,
)


def test_valid_feedback_request() -> None:
    message_id = uuid4()

    request = FeedbackRequest(
        session_id="feedback-schema-test",
        message_id=message_id,
        rating="up",
    )

    assert request.session_id == "feedback-schema-test"
    assert request.message_id == message_id
    assert request.rating == "up"


@pytest.mark.parametrize("rating", ["up", "down"])
def test_feedback_request_accepts_supported_ratings(
    rating: str,
) -> None:
    request = FeedbackRequest(
        session_id="feedback-schema-test",
        message_id=uuid4(),
        rating=rating,
    )

    assert request.rating == rating


def test_feedback_request_rejects_invalid_rating() -> None:
    with pytest.raises(ValidationError):
        FeedbackRequest(
            session_id="feedback-schema-test",
            message_id=uuid4(),
            rating="maybe",
        )


def test_feedback_request_rejects_invalid_message_id() -> None:
    with pytest.raises(ValidationError):
        FeedbackRequest(
            session_id="feedback-schema-test",
            message_id="not-a-uuid",
            rating="up",
        )


def test_valid_feedback_response() -> None:
    message_id = uuid4()

    response = FeedbackResponse(
        message_id=message_id,
        rating="down",
        status="saved",
    )

    assert response.model_dump() == {
        "message_id": message_id,
        "rating": "down",
        "status": "saved",
    }


def test_feedback_response_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        FeedbackResponse(
            message_id=uuid4(),
            rating="up",
            status="unknown",
        )

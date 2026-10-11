from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db.database import SessionLocal
from backend.app.main import app
from backend.app.models import ConversationSession, Feedback, Message
from backend.app.services.rate_limit_service import reset_rate_limit


client = TestClient(app)

FEEDBACK_API_SESSION_ID = "test-feedback-api"


def cleanup_feedback_test_data() -> None:
    database = SessionLocal()

    try:
        conversations = database.scalars(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == FEEDBACK_API_SESSION_ID
            )
        ).all()

        for conversation in conversations:
            database.delete(conversation)

        database.commit()

    finally:
        database.close()


@pytest.fixture(autouse=True)
def clean_feedback_test_data() -> None:
    reset_rate_limit(FEEDBACK_API_SESSION_ID)
    cleanup_feedback_test_data()

    yield

    reset_rate_limit(FEEDBACK_API_SESSION_ID)
    cleanup_feedback_test_data()


def create_assistant_message() -> str:
    response = client.post(
        "/api/chat",
        json={
            "message": "Bonjour",
            "session_id": FEEDBACK_API_SESSION_ID,
        },
    )

    assert response.status_code == 200

    return response.json()["message_id"]


def test_save_positive_feedback() -> None:
    message_id = create_assistant_message()

    response = client.post(
        "/api/feedback",
        json={
            "session_id": FEEDBACK_API_SESSION_ID,
            "message_id": message_id,
            "rating": "up",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message_id": message_id,
        "rating": "up",
        "status": "saved",
    }

    database = SessionLocal()

    try:
        feedback = database.scalar(
            select(Feedback).where(
                Feedback.message_id == message_id
            )
        )

        assert feedback is not None
        assert feedback.rating == "up"

    finally:
        database.close()


def test_update_existing_feedback_without_duplicate() -> None:
    message_id = create_assistant_message()

    first_response = client.post(
        "/api/feedback",
        json={
            "session_id": FEEDBACK_API_SESSION_ID,
            "message_id": message_id,
            "rating": "up",
        },
    )

    second_response = client.post(
        "/api/feedback",
        json={
            "session_id": FEEDBACK_API_SESSION_ID,
            "message_id": message_id,
            "rating": "down",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["rating"] == "down"

    database = SessionLocal()

    try:
        feedbacks = database.scalars(
            select(Feedback).where(
                Feedback.message_id == message_id
            )
        ).all()

        assert len(feedbacks) == 1
        assert feedbacks[0].rating == "down"

    finally:
        database.close()


def test_feedback_rejects_unknown_message() -> None:
    response = client.post(
        "/api/feedback",
        json={
            "session_id": FEEDBACK_API_SESSION_ID,
            "message_id": str(uuid4()),
            "rating": "up",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "message_not_found"


def test_feedback_rejects_wrong_session() -> None:
    message_id = create_assistant_message()

    response = client.post(
        "/api/feedback",
        json={
            "session_id": "another-session",
            "message_id": message_id,
            "rating": "up",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "message_not_found"


def test_feedback_rejects_invalid_rating() -> None:
    message_id = create_assistant_message()

    response = client.post(
        "/api/feedback",
        json={
            "session_id": FEEDBACK_API_SESSION_ID,
            "message_id": message_id,
            "rating": "maybe",
        },
    )

    assert response.status_code == 422


def test_feedback_rejects_user_message() -> None:
    create_assistant_message()

    database = SessionLocal()

    try:
        conversation = database.scalar(
            select(ConversationSession).where(
                ConversationSession.anonymous_user_id
                == FEEDBACK_API_SESSION_ID
            )
        )

        assert conversation is not None

        user_message = database.scalar(
            select(Message).where(
                Message.session_id == conversation.id,
                Message.role == "user",
            )
        )

        assert user_message is not None
        user_message_id = str(user_message.id)

    finally:
        database.close()

    response = client.post(
        "/api/feedback",
        json={
            "session_id": FEEDBACK_API_SESSION_ID,
            "message_id": user_message_id,
            "rating": "up",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "message_not_found"

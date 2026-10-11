import uuid
from datetime import datetime, timedelta, timezone

from backend.app.db.database import SessionLocal
from backend.app.models import ConversationSession, Feedback, Message
from backend.app.services.analytics_service import (
    build_summary,
    period_bounds,
    safe_rate,
)

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def create_session(db, started_at=NOW):
    session = ConversationSession(
        anonymous_user_id=f"anon-{uuid.uuid4()}",
        channel="web",
        language="fr",
        started_at=started_at,
    )
    db.add(session)
    db.flush()
    return session


def create_exchange(
    db,
    session,
    created_at,
    category="faq",
    source="FAQ",
    resolved=True,
    response_time_ms=100,
    rating=None,
):
    user = Message(
        session_id=session.id,
        role="user",
        content_redacted="question",
        created_at=created_at,
    )
    assistant = Message(
        session_id=session.id,
        role="assistant",
        content_redacted="réponse",
        created_at=created_at,
        response_time_ms=response_time_ms,
        category=category,
        source=source,
        confidence=0.9,
        resolved=resolved,
    )
    db.add_all((user, assistant))
    db.flush()
    if rating:
        db.add(Feedback(message_id=assistant.id, rating=rating, created_at=created_at))
        db.flush()
    return assistant


def test_safe_rate_handles_zero_denominator() -> None:
    assert safe_rate(0, 0) == 0.0
    assert safe_rate(1, 3) == 0.333


def test_period_bounds_use_given_now() -> None:
    start, end = period_bounds(7, now=NOW)

    assert end == NOW
    assert start == NOW - timedelta(days=7)


def test_empty_summary_returns_zeros() -> None:
    db = SessionLocal()
    try:
        summary = build_summary(db, days=30, now=NOW)
    finally:
        db.close()

    assert summary["period"]["days"] == 30
    assert summary["sessions"] == {"total": 0}
    assert summary["messages"] == {"total": 0, "user": 0, "assistant": 0}
    assert summary["resolution"] == {"resolved": 0, "unresolved": 0, "rate": 0.0}
    assert summary["response_time_ms"] == {"average": None, "max": None}
    assert summary["feedback"]["satisfaction_rate"] == 0.0
    assert summary["categories"] == []
    assert summary["sources"] == []
    assert summary["daily"] == []


def test_summary_aggregates_only_period_data() -> None:
    db = SessionLocal()
    try:
        session = create_session(db)
        create_exchange(db, session, NOW - timedelta(hours=1), rating="up")
        create_exchange(
            db,
            session,
            NOW - timedelta(hours=2),
            category="procedure",
            source="Procédures",
            response_time_ms=300,
            rating="up",
        )
        create_exchange(
            db,
            session,
            NOW - timedelta(days=1),
            resolved=False,
            response_time_ms=200,
            rating="down",
        )
        old_session = create_session(db, started_at=NOW - timedelta(days=40))
        create_exchange(db, old_session, NOW - timedelta(days=40), rating="down")
        db.commit()

        summary = build_summary(db, days=30, now=NOW)
    finally:
        db.close()

    assert summary["sessions"] == {"total": 1}
    assert summary["messages"] == {"total": 6, "user": 3, "assistant": 3}
    assert summary["resolution"] == {"resolved": 2, "unresolved": 1, "rate": 0.667}
    assert summary["response_time_ms"] == {"average": 200.0, "max": 300}
    assert summary["feedback"] == {
        "total": 3,
        "up": 2,
        "down": 1,
        "satisfaction_rate": 0.667,
    }
    assert summary["categories"] == [
        {"category": "faq", "count": 2},
        {"category": "procedure", "count": 1},
    ]
    assert summary["sources"] == [
        {"source": "FAQ", "count": 2},
        {"source": "Procédures", "count": 1},
    ]
    assert len(summary["daily"]) == 2
    assert summary["daily"][0]["date"] == (NOW - timedelta(days=1)).date()
    assert summary["daily"][0] == {
        "date": (NOW - timedelta(days=1)).date(),
        "messages": 2,
        "sessions": 0,
    }
    assert summary["daily"][1] == {"date": NOW.date(), "messages": 4, "sessions": 1}

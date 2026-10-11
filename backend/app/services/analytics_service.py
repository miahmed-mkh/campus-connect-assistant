"""Agrégations d'usage pour le tableau de bord analytics.

Toutes les fonctions sont pures : elles prennent une session SQLAlchemy
et une fenêtre temporelle, et renvoient des dictionnaires validés ensuite
par les schémas Pydantic de la route.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.app.models import ConversationSession, Feedback, Message

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
TOP_LIMIT = 20


def period_bounds(
    days: int,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    end = now or datetime.now(timezone.utc)
    return end - timedelta(days=days), end


def safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 3)


def session_stats(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    total = db.scalar(
        select(func.count(ConversationSession.id)).where(
            ConversationSession.started_at >= start,
            ConversationSession.started_at <= end,
        )
    )
    return {"total": int(total or 0)}


def message_stats(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    total, user, assistant = db.execute(
        select(
            func.count(Message.id),
            func.count(case((Message.role == USER_ROLE, 1))),
            func.count(case((Message.role == ASSISTANT_ROLE, 1))),
        ).where(Message.created_at >= start, Message.created_at <= end)
    ).one()
    return {"total": total, "user": user, "assistant": assistant}


def resolution_stats(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    resolved, unresolved = db.execute(
        select(
            func.count(case((Message.resolved.is_(True), 1))),
            func.count(case((Message.resolved.is_(False), 1))),
        ).where(
            Message.role == ASSISTANT_ROLE,
            Message.created_at >= start,
            Message.created_at <= end,
        )
    ).one()
    return {
        "resolved": resolved,
        "unresolved": unresolved,
        "rate": safe_rate(resolved, resolved + unresolved),
    }


def response_time_stats(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    average, maximum = db.execute(
        select(
            func.avg(Message.response_time_ms),
            func.max(Message.response_time_ms),
        ).where(
            Message.role == ASSISTANT_ROLE,
            Message.response_time_ms.is_not(None),
            Message.created_at >= start,
            Message.created_at <= end,
        )
    ).one()
    return {
        "average": round(float(average), 1) if average is not None else None,
        "max": int(maximum) if maximum is not None else None,
    }


def feedback_stats(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    total, up, down = db.execute(
        select(
            func.count(Feedback.id),
            func.count(case((Feedback.rating == "up", 1))),
            func.count(case((Feedback.rating == "down", 1))),
        ).where(Feedback.created_at >= start, Feedback.created_at <= end)
    ).one()
    return {
        "total": total,
        "up": up,
        "down": down,
        "satisfaction_rate": safe_rate(up, total),
    }


def _top_counts(db: Session, column, key: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    rows = db.execute(
        select(column, func.count(Message.id).label("count"))
        .where(
            Message.role == ASSISTANT_ROLE,
            column.is_not(None),
            Message.created_at >= start,
            Message.created_at <= end,
        )
        .group_by(column)
        .order_by(func.count(Message.id).desc(), column.asc())
        .limit(TOP_LIMIT)
    ).all()
    return [{key: value, "count": count} for value, count in rows]


def category_counts(db: Session, start: datetime, end: datetime) -> list[dict[str, Any]]:
    return _top_counts(db, Message.category, "category", start, end)


def source_counts(db: Session, start: datetime, end: datetime) -> list[dict[str, Any]]:
    return _top_counts(db, Message.source, "source", start, end)


def daily_counts(db: Session, start: datetime, end: datetime) -> list[dict[str, Any]]:
    daily: dict[date, dict[str, int]] = {}

    message_day = func.date(Message.created_at)
    for day, count in db.execute(
        select(message_day, func.count(Message.id))
        .where(Message.created_at >= start, Message.created_at <= end)
        .group_by(message_day)
    ).all():
        daily.setdefault(day, {"messages": 0, "sessions": 0})["messages"] = count

    session_day = func.date(ConversationSession.started_at)
    for day, count in db.execute(
        select(session_day, func.count(ConversationSession.id))
        .where(
            ConversationSession.started_at >= start,
            ConversationSession.started_at <= end,
        )
        .group_by(session_day)
    ).all():
        daily.setdefault(day, {"messages": 0, "sessions": 0})["sessions"] = count

    return [{"date": day, **counts} for day, counts in sorted(daily.items())]


def build_summary(db: Session, days: int, now: datetime | None = None) -> dict[str, Any]:
    start, end = period_bounds(days, now)
    return {
        "period": {"days": days, "start": start, "end": end},
        "sessions": session_stats(db, start, end),
        "messages": message_stats(db, start, end),
        "resolution": resolution_stats(db, start, end),
        "response_time_ms": response_time_stats(db, start, end),
        "feedback": feedback_stats(db, start, end),
        "categories": category_counts(db, start, end),
        "sources": source_counts(db, start, end),
        "daily": daily_counts(db, start, end),
    }

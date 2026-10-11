from datetime import date, datetime

from pydantic import BaseModel, Field


class AnalyticsPeriod(BaseModel):
    days: int = Field(ge=1, le=365)
    start: datetime
    end: datetime


class SessionStats(BaseModel):
    total: int


class MessageStats(BaseModel):
    total: int
    user: int
    assistant: int


class ResolutionStats(BaseModel):
    resolved: int
    unresolved: int
    rate: float


class ResponseTimeStats(BaseModel):
    average: float | None
    max: int | None


class FeedbackStats(BaseModel):
    total: int
    up: int
    down: int
    satisfaction_rate: float


class CategoryCount(BaseModel):
    category: str
    count: int


class SourceCount(BaseModel):
    source: str
    count: int


class DailyCount(BaseModel):
    date: date
    messages: int
    sessions: int


class AnalyticsSummary(BaseModel):
    period: AnalyticsPeriod
    sessions: SessionStats
    messages: MessageStats
    resolution: ResolutionStats
    response_time_ms: ResponseTimeStats
    feedback: FeedbackStats
    categories: list[CategoryCount]
    sources: list[SourceCount]
    daily: list[DailyCount]

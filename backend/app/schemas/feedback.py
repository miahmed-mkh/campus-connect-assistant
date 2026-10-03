from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: UUID
    rating: Literal["up", "down"]


class FeedbackResponse(BaseModel):
    message_id: UUID
    rating: Literal["up", "down"]
    status: Literal["saved"]

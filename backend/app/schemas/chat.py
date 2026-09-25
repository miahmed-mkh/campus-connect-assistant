from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000,
        description="Question envoyée par l'utilisateur",
    )

    session_id: str = Field(
        min_length=1,
        max_length=100,
        description="Identifiant de la session de conversation",
    )


class ChatResponse(BaseModel):
    answer: str
    source: str | None = None
    category: str
    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    resolved: bool

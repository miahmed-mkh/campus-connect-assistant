from pydantic import BaseModel, Field


class RateLimitResult(BaseModel):
    allowed: bool
    limit: int = Field(ge=1)
    remaining: int = Field(ge=0)
    retry_after_seconds: int = Field(ge=0)

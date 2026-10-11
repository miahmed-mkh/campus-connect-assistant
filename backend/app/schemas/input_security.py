from pydantic import BaseModel


class InputSecurityResult(BaseModel):
    is_safe: bool
    reason: str | None = None
    sanitized_text: str

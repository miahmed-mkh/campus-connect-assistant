from pydantic import BaseModel, Field, field_validator


EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_PATTERN)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le nom ne peut pas être vide.")
        return value


class LoginRequest(BaseModel):
    # E-mail pour un compte créé, identifiant pour un compte de la console
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    token: str
    username: str
    role: str
    display_name: str
    expires_in: int

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Campus Connect Assistant API"
    app_description: str = (
        "API de l'assistant virtuel éducatif du Campus ESIC"
    )
    app_version: str = "0.1.0"
    app_environment: str = "development"

    database_url: str = (
        "postgresql+psycopg://campus_user:change_me"
        "@127.0.0.1:5433/campus_connect"
    )

    docker_database_url: str = (
        "postgresql+psycopg://campus_user:change_me"
        "@postgres:5432/campus_connect"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

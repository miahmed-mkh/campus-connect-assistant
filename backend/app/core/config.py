from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Campus Connect Assistant API"
    app_description: str = (
        "API de l'assistant virtuel éducatif du Campus ESIC"
    )
    app_version: str = "1.2.0"
    app_environment: str = "development"

    # Cle d'acces aux statistiques d'usage (vide = endpoint desactive)
    analytics_api_key: str = ""
    iot_device_key: str = ""
    iot_online_threshold_seconds: int = 120

    # Console IoT : secret de signature des jetons et hachage des comptes
    console_token_secret: str = ""
    console_token_ttl_seconds: int = 3600
    console_responsable_hash: str = ""
    console_intervenant_hash: str = ""
    console_etudiant_hash: str = ""

    database_url: str = (
        "postgresql+psycopg://campus_user:change_me"
        "@127.0.0.1:5433/campus_connect"
    )

    # LLM : reformulation locale via Ollama
    llm_enabled: bool = False
    llm_base_url: str = "http://ollama:11434"
    llm_model: str = "qwen2.5:1.5b"
    llm_timeout_seconds: float = 8.0
    llm_max_passage_chars: int = 600
    llm_keep_alive: str = "10m"

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

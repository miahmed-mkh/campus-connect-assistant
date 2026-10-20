"""Isolation des tests sur une base PostgreSQL dédiée.

L'URL de test est positionnée dans l'environnement AVANT tout import de
l'application : pydantic-settings donne la priorité aux variables
d'environnement sur le fichier .env, donc l'engine, les sessions et
Alembic basculent sur la base de test sans modifier le code de production.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_SUFFIX = "_test"
TABLES_TO_TRUNCATE = (
    "feedbacks",
    "messages",
    "conversation_sessions",
    "iot_readings",
)


def resolve_test_database_url() -> str:
    env_file = dotenv_values(PROJECT_ROOT / ".env")

    explicit = os.environ.get("TEST_DATABASE_URL") or env_file.get(
        "TEST_DATABASE_URL"
    )
    if explicit:
        return explicit

    base = os.environ.get("DATABASE_URL") or env_file.get("DATABASE_URL")
    if not base:
        raise RuntimeError(
            "DATABASE_URL introuvable (variable d'environnement ou .env)"
        )

    url = make_url(base)
    derived = url.set(database=f"{url.database}{TEST_DATABASE_SUFFIX}")
    return derived.render_as_string(hide_password=False)


TEST_DATABASE_URL = resolve_test_database_url()
TEST_DATABASE_NAME = make_url(TEST_DATABASE_URL).database or ""

if not TEST_DATABASE_NAME.endswith(TEST_DATABASE_SUFFIX):
    raise RuntimeError(
        f"Refus de lancer les tests : la base '{TEST_DATABASE_NAME}' "
        f"ne se termine pas par '{TEST_DATABASE_SUFFIX}'"
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# Les tests ne chargent jamais le vrai modele : ils utilisent un encodeur
# simule (voir test_semantic_service.py).
os.environ["SEMANTIC_ENABLED"] = "false"


def ensure_test_database_exists() -> None:
    maintenance_url = make_url(TEST_DATABASE_URL).set(database="postgres")
    engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")

    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE_NAME},
        ).scalar()
        if not exists:
            connection.execute(
                text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"')
            )

    engine.dispose()


def apply_migrations() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
    )


@pytest.fixture(scope="session", autouse=True)
def test_database() -> None:
    ensure_test_database_exists()
    apply_migrations()


@pytest.fixture(autouse=True)
def clean_tables(test_database):
    yield

    from backend.app.db.database import engine

    with engine.begin() as connection:
        connection.execute(
            text(
                f"TRUNCATE TABLE {', '.join(TABLES_TO_TRUNCATE)} "
                "RESTART IDENTITY CASCADE"
            )
        )

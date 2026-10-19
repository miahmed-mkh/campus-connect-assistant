import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import auth as auth_api
from backend.app.core.console_auth import hash_password
from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.models import User


@pytest.fixture
def client(monkeypatch):
    # Base SQLite en mémoire, limitée à la table users
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        database = TestingSession()
        try:
            yield database
        finally:
            database.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(auth_api.settings, "console_token_secret", "secret-de-test")
    # Hachage rapide pour les tests
    monkeypatch.setattr(
        auth_api, "hash_password", lambda password: hash_password(password, iterations=1000)
    )

    yield TestClient(app)

    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    engine.dispose()


def register(client, email="emma@esic.fr", password="motdepasse1", name="Emma"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "display_name": name, "password": password},
    )


def test_register_creates_student_account(client):
    response = register(client, email="  Emma@ESIC.fr ")

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "emma@esic.fr"
    assert data["role"] == "etudiant"
    assert data["display_name"] == "Emma"
    assert data["token"]


def test_register_rejects_duplicate_email(client):
    register(client)
    response = register(client, email="EMMA@esic.fr")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "email_taken"


def test_register_rejects_short_password(client):
    assert register(client, password="court").status_code == 422


def test_register_rejects_invalid_email(client):
    assert register(client, email="pas-un-email").status_code == 422


def test_login_with_created_account(client):
    register(client)
    response = client.post(
        "/api/auth/login",
        json={"username": "emma@esic.fr", "password": "motdepasse1"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "etudiant"


def test_login_wrong_password(client):
    register(client)
    response = client.post(
        "/api/auth/login",
        json={"username": "emma@esic.fr", "password": "mauvais"},
    )

    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "inconnu@esic.fr", "password": "motdepasse1"},
    )

    assert response.status_code == 401


def test_login_console_account(client, monkeypatch):
    monkeypatch.setattr(
        auth_api.settings,
        "console_responsable_hash",
        hash_password("admin-pass", iterations=1000),
    )
    response = client.post(
        "/api/auth/login",
        json={"username": "responsable.si", "password": "admin-pass"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "responsable"


def test_auth_disabled_without_secret(client, monkeypatch):
    monkeypatch.setattr(auth_api.settings, "console_token_secret", "")

    assert register(client).status_code == 503

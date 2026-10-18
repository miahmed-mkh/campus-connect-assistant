import pytest
from fastapi.testclient import TestClient

from backend.app.core import console_auth
from backend.app.core.config import settings
from backend.app.main import app

client = TestClient(app)

LOGIN_URL = "/api/iot/console/login"
SECRET = "secret-de-test-pour-la-console-iot"
FAST = 1000

ACCOUNTS = {
    "responsable.si": ("responsable", "mdp-test-responsable"),
    "intervenant.maintenance": ("intervenant", "mdp-test-intervenant"),
    "etudiant.demo": ("etudiant", "mdp-test-etudiant"),
}


@pytest.fixture
def console_accounts(monkeypatch):
    monkeypatch.setattr(settings, "console_token_secret", SECRET)
    monkeypatch.setattr(settings, "console_token_ttl_seconds", 3600)
    monkeypatch.setattr(
        settings,
        "console_responsable_hash",
        console_auth.hash_password(ACCOUNTS["responsable.si"][1], FAST),
    )
    monkeypatch.setattr(
        settings,
        "console_intervenant_hash",
        console_auth.hash_password(
            ACCOUNTS["intervenant.maintenance"][1], FAST
        ),
    )
    monkeypatch.setattr(
        settings,
        "console_etudiant_hash",
        console_auth.hash_password(ACCOUNTS["etudiant.demo"][1], FAST),
    )


def login(username: str, password: str):
    return client.post(
        LOGIN_URL, json={"username": username, "password": password}
    )


@pytest.mark.parametrize("username", list(ACCOUNTS))
def test_login_succeeds_for_each_account(console_accounts, username) -> None:
    role, password = ACCOUNTS[username]

    response = login(username, password)

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == username
    assert body["role"] == role
    assert body["expires_in"] == 3600
    assert body["display_name"]
    assert password not in response.text


@pytest.mark.parametrize("username", list(ACCOUNTS))
def test_login_returns_a_valid_signed_token(
    console_accounts, username
) -> None:
    role, password = ACCOUNTS[username]

    token = login(username, password).json()["token"]
    payload = console_auth.verify_token(token, SECRET)

    assert payload is not None
    assert payload["sub"] == username
    assert payload["role"] == role


def test_login_rejects_wrong_password(console_accounts) -> None:
    response = login("responsable.si", "mauvais-mot-de-passe")

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_credentials"
    assert "token" not in response.text


def test_unknown_account_gets_same_error_as_wrong_password(
    console_accounts,
) -> None:
    wrong_password = login("responsable.si", "mauvais-mot-de-passe")
    unknown = login("inconnu.demo", "mauvais-mot-de-passe")

    assert unknown.status_code == 401
    assert unknown.json() == wrong_password.json()


def test_account_without_configured_hash_cannot_login(
    console_accounts, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "console_etudiant_hash", "")

    response = login("etudiant.demo", ACCOUNTS["etudiant.demo"][1])

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_credentials"


def test_login_returns_503_when_secret_is_not_configured(
    console_accounts, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "console_token_secret", "")

    response = login("responsable.si", ACCOUNTS["responsable.si"][1])

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "console_disabled"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "responsable.si"},
        {"password": "x"},
        {"username": "", "password": "x"},
        {"username": "responsable.si", "password": ""},
    ],
)
def test_login_rejects_invalid_payload(console_accounts, payload) -> None:
    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == 422

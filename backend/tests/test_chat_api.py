from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_chat_with_known_question() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "À quelle heure est ouverte la scolarité ?",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "Le service scolarité est ouvert du lundi au vendredi, "
            "de 9h à 17h."
        ),
        "source": "Guide de l'étudiant",
    }


def test_chat_with_greeting() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "Bonjour",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "Bonjour ! Posez-moi votre question sur le campus, "
            "je suis là pour vous aider."
        ),
        "source": None,
    }


def test_chat_with_unknown_question() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "Comment réserver un hélicoptère sur le campus ?",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["source"] is None
    assert "pas encore de réponse fiable" in data["answer"]


def test_chat_rejects_empty_message() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "",
            "session_id": "session-001",
        },
    )

    assert response.status_code == 422


def test_chat_rejects_missing_session_id() -> None:
    response = client.post(
        "/api/chat",
        json={
            "message": "Bonjour",
        },
    )

    assert response.status_code == 422

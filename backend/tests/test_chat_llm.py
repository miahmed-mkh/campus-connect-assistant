import sys

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.rate_limit_service import reset_rate_limit

client = TestClient(app)

chat_module = sys.modules["backend.app.api.chat"]

REPONSE_MOTEUR = "reponse du moteur"
REPONSE_LLM = "reponse reformulee"


def poser_question(monkeypatch, categorie: str, session_id: str, llm_renvoie):
    appels = []

    def fake_search(question: str, language: str = "fr") -> dict:
        return {
            "answer": REPONSE_MOTEUR,
            "source": None,
            "category": categorie,
            "confidence": 0.9,
        }

    def fake_rephrase(question: str, passage: str):
        appels.append((question, passage))
        return llm_renvoie

    monkeypatch.setattr(chat_module, "search_knowledge", fake_search)
    monkeypatch.setattr(chat_module, "rephrase_answer", fake_rephrase)

    reset_rate_limit(session_id)
    response = client.post(
        "/api/chat",
        json={"message": "question de test", "session_id": session_id},
    )
    reset_rate_limit(session_id)

    return response, appels


@pytest.mark.parametrize("categorie", ["faq", "document"])
def test_categories_reformulees_par_le_llm(monkeypatch, categorie) -> None:
    response, appels = poser_question(
        monkeypatch, categorie, f"test-chat-llm-{categorie}", REPONSE_LLM
    )

    assert response.status_code == 200
    assert response.json()["answer"] == REPONSE_LLM
    assert response.json()["category"] == categorie
    assert appels == [("question de test", REPONSE_MOTEUR)]


@pytest.mark.parametrize("categorie", ["schedule", "contact", "unknown", "procedure"])
def test_categories_exclues_jamais_envoyees_au_llm(monkeypatch, categorie) -> None:
    response, appels = poser_question(
        monkeypatch, categorie, f"test-chat-llm-exclu-{categorie}", REPONSE_LLM
    )

    assert response.status_code == 200
    assert response.json()["answer"] == REPONSE_MOTEUR
    assert appels == []


def test_repli_sur_le_moteur_si_le_llm_ne_repond_pas(monkeypatch) -> None:
    response, appels = poser_question(
        monkeypatch, "faq", "test-chat-llm-repli", None
    )

    assert response.status_code == 200
    assert response.json()["answer"] == REPONSE_MOTEUR
    assert len(appels) == 1



def test_question_masquee_avant_envoi_au_llm(monkeypatch) -> None:
    questions = []

    def fake_search(question: str, language: str = "fr") -> dict:
        return {
            "answer": REPONSE_MOTEUR,
            "source": None,
            "category": "faq",
            "confidence": 0.9,
        }

    def fake_rephrase(question: str, passage: str):
        questions.append(question)
        return None

    monkeypatch.setattr(chat_module, "search_knowledge", fake_search)
    monkeypatch.setattr(chat_module, "rephrase_answer", fake_rephrase)

    session_id = "test-chat-llm-pii"
    reset_rate_limit(session_id)
    response = client.post(
        "/api/chat",
        json={
            "message": "mon mail est jean.dupont@example.com, aide moi",
            "session_id": session_id,
        },
    )
    reset_rate_limit(session_id)

    assert response.status_code == 200
    assert len(questions) == 1
    assert "jean.dupont@example.com" not in questions[0]
    assert "[EMAIL]" in questions[0]

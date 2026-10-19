import sys

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.rate_limit_service import reset_rate_limit

client = TestClient(app)

SESSION_ID = "test-chat-unescape"


def test_engine_receives_unescaped_question(monkeypatch) -> None:
    received = []

    def fake_search(question: str) -> dict:
        received.append(question)
        return {
            "answer": "reponse de test",
            "source": None,
            "category": "faq",
            "confidence": 0.9,
        }

    chat_module = sys.modules["backend.app.api.chat"]
    monkeypatch.setattr(chat_module, "search_knowledge", fake_search)

    reset_rate_limit(SESSION_ID)
    response = client.post(
        "/api/chat",
        json={
            "message": "j'ai perdu ma carte",
            "session_id": SESSION_ID,
        },
    )
    reset_rate_limit(SESSION_ID)

    assert response.status_code == 200
    assert received == ["j'ai perdu ma carte"]

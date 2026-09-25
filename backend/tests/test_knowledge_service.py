from backend.app.services.knowledge_service import (
    knowledge_service,
    normalize_text,
)


def test_normalize_text() -> None:
    normalized = normalize_text(
        "  À quelle heure ouvre la Scolarité ?  "
    )

    assert normalized == "a quelle heure ouvre la scolarite"


def test_exact_question_returns_expected_answer() -> None:
    result = knowledge_service.search(
        "Quels sont les horaires de la scolarité ?"
    )

    assert result["category"] == "service_campus"
    assert result["source"] == "Guide de l'étudiant"
    assert result["confidence"] == 1.0
    assert "9h à 17h" in result["answer"]


def test_rephrased_question_returns_expected_answer() -> None:
    result = knowledge_service.search(
        "À quelle heure est ouverte la scolarité ?"
    )

    assert result["category"] == "service_campus"
    assert result["source"] == "Guide de l'étudiant"
    assert result["confidence"] >= 0.65


def test_greeting_returns_answer_without_source() -> None:
    result = knowledge_service.search("Bonjour")

    assert result["category"] == "salutation"
    assert result["source"] is None
    assert result["confidence"] == 1.0


def test_unknown_question_returns_fallback() -> None:
    result = knowledge_service.search(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["category"] == "unknown"
    assert result["source"] is None
    assert result["confidence"] < 0.65
    assert "pas encore de réponse fiable" in result["answer"]
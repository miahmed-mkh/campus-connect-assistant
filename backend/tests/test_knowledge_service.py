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

def test_expanded_faq_library_question() -> None:
    result = knowledge_service.search(
        "Quels sont les horaires de la bibliothèque ?"
    )

    assert result["category"] == "services_campus"
    assert result["confidence"] == 1.0
    assert result["source"] == (
        "FAQ complète ESIC — données pédagogiques 2024-2025"
    )
    assert "bibliothèque" in result["answer"].lower()


def test_administrative_question_preserves_legacy_answer() -> None:
    result = knowledge_service.search(
        "Comment obtenir un certificat de scolarité ?"
    )

    assert result["category"] == "procedure_admin"
    assert result["confidence"] == 1.0
    assert result["source"] == "Procédures administratives"
    assert "ENT" in result["answer"]


def test_expanded_faq_orientation_question() -> None:
    result = knowledge_service.search(
        "Quelles sont les spécialisations proposées en Bachelor 3 ?"
    )

    assert result["category"] == "orientation_formation"
    assert result["confidence"] >= 0.65
    assert result["source"] == (
        "FAQ complète ESIC — données pédagogiques 2024-2025"
    )
    assert "Cybersécurité" in result["answer"]


def test_knowledge_service_loads_all_faq_items() -> None:
    assert len(knowledge_service.faq_items) == 159

    identifiers = [
        item["id"]
        for item in knowledge_service.faq_items
    ]

    assert len(identifiers) == len(set(identifiers))


def test_expanded_faq_library_question() -> None:
    result = knowledge_service.search(
        "Quels sont les horaires de la bibliothèque ?"
    )

    assert result["category"] == "services_campus"
    assert result["confidence"] == 1.0
    assert result["source"] == (
        "FAQ complète ESIC — données pédagogiques 2024-2025"
    )
    assert "bibliothèque" in result["answer"].lower()


def test_administrative_question_preserves_legacy_answer() -> None:
    result = knowledge_service.search(
        "Comment obtenir un certificat de scolarité ?"
    )

    assert result["category"] == "procedure_admin"
    assert result["confidence"] == 1.0
    assert result["source"] == "Procédures administratives"
    assert "ENT" in result["answer"]


def test_expanded_faq_orientation_question() -> None:
    result = knowledge_service.search(
        "Quelles sont les spécialisations proposées en Bachelor 3 ?"
    )

    assert result["category"] == "orientation_formation"
    assert result["confidence"] >= 0.65
    assert result["source"] == (
        "FAQ complète ESIC — données pédagogiques 2024-2025"
    )
    assert "Cybersécurité" in result["answer"]


def test_knowledge_service_loads_all_faq_items() -> None:
    assert len(knowledge_service.faq_items) == 159

    identifiers = [
        item["id"]
        for item in knowledge_service.faq_items
    ]

    assert len(identifiers) == len(set(identifiers))

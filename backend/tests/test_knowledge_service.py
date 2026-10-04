from backend.app.services.knowledge_service import (
    knowledge_service,
    normalize_text,
)

from backend.app.services.knowledge_service import (
    search_knowledge,
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

def test_search_knowledge_selects_procedure() -> None:
    result = search_knowledge(
        "Quels documents faut-il pour une convention de stage ?"
    )

    assert result["category"] == "procedure"
    assert result["confidence"] >= 0.65
    assert result["source"] == (
        "Procédures ESIC — données pédagogiques 2024-2025"
    )
    assert "Convention de Stage" in result["answer"]


def test_search_knowledge_preserves_faq_answer() -> None:
    result = search_knowledge(
        "Quels sont les horaires de la bibliothèque ?"
    )

    assert result["category"] == "services_campus"
    assert result["confidence"] == 1.0
    assert result["source"] == (
        "FAQ complète ESIC — données pédagogiques 2024-2025"
    )


def test_search_knowledge_preserves_greeting() -> None:
    result = search_knowledge("Bonjour")

    assert result["category"] == "salutation"
    assert result["confidence"] == 1.0
    assert result["source"] is None


def test_search_knowledge_returns_unknown() -> None:
    result = search_knowledge(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["category"] == "unknown"
    assert result["confidence"] < 0.65
    assert result["source"] is None

def test_global_search_returns_procedure_result() -> None:
    result = search_knowledge(
        "Quels documents faut-il pour une convention de stage ?"
    )

    assert result["category"] == "procedure"
    assert result["confidence"] >= 0.65
    assert result["source"] is not None


def test_global_search_returns_teacher_contact() -> None:
    result = search_knowledge(
        "Qui enseigne l'algorithmique ?"
    )

    assert result["category"] == "contact"
    assert result["confidence"] >= 0.65
    assert "bernard" in result["answer"].lower()


def test_global_search_returns_external_partner_contact() -> None:
    result = search_knowledge(
        "Comment contacter le CROUS de Paris ?"
    )

    assert result["category"] == "contact"
    assert result["confidence"] >= 0.65
    assert "crous" in result["answer"].lower()


def test_global_search_preserves_faq_result() -> None:
    result = search_knowledge(
        "Quels sont les horaires de la bibliothèque ?"
    )

    assert result["category"] == "services_campus"
    assert result["confidence"] == 1.0


def test_global_search_returns_unknown_for_unavailable_service() -> None:
    result = search_knowledge(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["category"] == "unknown"
    assert result["source"] is None
    assert result["confidence"] < 0.65

def test_global_search_returns_plagiarism_document() -> None:
    result = search_knowledge(
        "Quelles sont les sanctions en cas de plagiat ?"
    )

    assert result["category"] == "document"
    assert result["confidence"] >= 0.55
    assert result["source"] is not None
    assert "2024-2025" in result["answer"]
    assert "non officiels" in result["answer"]


def test_global_search_returns_absence_document() -> None:
    result = search_knowledge(
        "Comment justifier une absence ?"
    )

    assert result["category"] == "document"
    assert result["confidence"] >= 0.55
    assert "absence" in result["answer"].lower()


def test_document_integration_preserves_contact_result() -> None:
    result = search_knowledge(
        "Qui enseigne l'algorithmique ?"
    )

    assert result["category"] == "contact"


def test_document_integration_preserves_procedure_result() -> None:
    result = search_knowledge(
        "Quels documents faut-il pour une convention de stage ?"
    )

    assert result["category"] == "procedure"


def test_document_integration_preserves_schedule_result() -> None:
    result = search_knowledge(
        "Quels sont les cours du groupe B1-A lundi ?"
    )

    assert result["category"] == "schedule"


def test_document_integration_preserves_faq_result() -> None:
    result = search_knowledge(
        "Quels sont les horaires de la bibliothèque ?"
    )

    assert result["category"] == "services_campus"


def test_document_integration_preserves_unknown_result() -> None:
    result = search_knowledge(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["category"] == "unknown"
    assert result["source"] is None
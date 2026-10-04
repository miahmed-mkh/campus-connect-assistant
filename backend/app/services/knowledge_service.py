from backend.app.services.text_matching import normalize_text
from difflib import SequenceMatcher
from typing import Any

from backend.app.services.contact_service import contact_service
from backend.app.services.document_service import document_service
from backend.app.services.faq_loader import load_all_faq_items
from backend.app.services.procedure_service import (
    procedure_service,
)
from backend.app.services.schedule_service import schedule_service


def calculate_similarity(
    normalized_question: str,
    normalized_reference: str,
) -> float:
    if normalized_question == normalized_reference:
        return 1.0

    question_words = set(normalized_question.split())
    reference_words = set(normalized_reference.split())
    common_words = question_words & reference_words

    if len(common_words) < 2:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        normalized_question,
        normalized_reference,
    ).ratio()

    question_coverage = len(common_words) / max(
        1,
        len(question_words),
    )

    reference_coverage = len(common_words) / max(
        1,
        len(reference_words),
    )

    return (
        sequence_score * 0.5
        + question_coverage * 0.3
        + reference_coverage * 0.2
    )

class KnowledgeService:
    def __init__(self) -> None:
        self.faq_items: list[dict[str, Any]] = (
            load_all_faq_items()
        )

    def search(self, question: str) -> dict[str, Any]:
        normalized_question = normalize_text(question)

        best_item: dict[str, Any] | None = None
        best_score = 0.0

        for item in self.faq_items:
            for reference_question in item["questions"]:
                normalized_reference = normalize_text(
                    reference_question
                )

                score = calculate_similarity(
                    normalized_question,
                    normalized_reference,
                )

                if score > best_score:
                    best_score = score
                    best_item = item

        if best_item is None or best_score < 0.65:
            return {
                "answer": (
                    "Je n’ai pas encore de réponse fiable à cette "
                    "question. Vous pouvez reformuler ou contacter "
                    "directement le service scolarité."
                ),
                "source": None,
                "category": "unknown",
                "confidence": round(best_score, 3),
            }

        return {
            "answer": best_item["answer"],
            "source": best_item["source"],
            "category": best_item["category"],
            "confidence": round(best_score, 3),
        }

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


def test_expanded_faq_administrative_question() -> None:
    result = knowledge_service.search(
        "Comment obtenir un certificat de scolarité ?"
    )

    assert result["category"] == "procedures_administratives"
    assert result["confidence"] >= 0.65
    assert result["source"] == (
        "FAQ complète ESIC — données pédagogiques 2024-2025"
    )


def test_expanded_faq_orientation_question() -> None:
    result = knowledge_service.search(
        "Quelles sont les spécialisations proposées en Bachelor 3 ?"
    )

    assert result["category"] == "orientation_formation"
    assert result["confidence"] >= 0.65
    assert result["source"] == (
        "FAQ complète ESIC — données pédagogiques 2024-2025"
    )

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

knowledge_service = KnowledgeService()

def search_knowledge(question: str) -> dict[str, Any]:
    results = (
        knowledge_service.search(question),
        procedure_service.search(question),
        contact_service.search(question),
        schedule_service.search(question),
        document_service.search(question),
    )

    known_results = tuple(
        result
        for result in results
        if result["category"] != "unknown"
    )

    if known_results:
        best_result = max(
            known_results,
            key=lambda result: result["confidence"],
        )

        return {
            "answer": best_result["answer"],
            "source": best_result["source"],
            "category": best_result["category"],
            "confidence": best_result["confidence"],
        }

    return results[0]

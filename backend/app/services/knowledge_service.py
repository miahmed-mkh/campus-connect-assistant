import logging
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
from backend.app.services.semantic_service import semantic_service
from backend.app.services.knowledge_ranking import (
    UNKNOWN_CATEGORY,
    RankedCandidate,
    build_candidate,
    explain_ranking,
    rank_candidates,
    select_answer,
)

logger = logging.getLogger(__name__)


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
    minimum_confidence = 0.65

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

        if best_item is None or best_score < self.minimum_confidence:
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


knowledge_service = KnowledgeService()

CLARIFICATION_CATEGORY = "clarification"

CLARIFICATION_ANSWER = (
    "Je ne suis pas sûr d’avoir bien compris. "
    "Vouliez-vous dire :"
)


def build_faq_candidates(
    faq_result: dict[str, Any],
    semantic_result: dict[str, Any],
) -> tuple[RankedCandidate, ...]:
    faq_candidate = build_candidate(
        "faq",
        faq_result,
        knowledge_service.minimum_confidence,
    )

    semantic_candidate = build_candidate(
        "semantic",
        semantic_result,
        semantic_service.minimum_confidence,
    )

    # Les deux candidats interrogent la même FAQ. S'ils sont en désaccord,
    # le sémantique comprend mieux le sens que le recouvrement de mots
    # (« bibliothèque » contre « scolarité ») : il remplace le lexical,
    # sauf correspondance exacte. S'ils sont d'accord, les deux restent
    # en lice et le plus confiant garde sa marge face aux autres sources.
    if (
        semantic_candidate.accepted
        and faq_candidate.confidence < 1.0
        and faq_candidate.answer != semantic_candidate.answer
    ):
        return (semantic_candidate,)

    return (faq_candidate, semantic_candidate)


def build_clarification(
    semantic_result: dict[str, Any],
) -> dict[str, Any] | None:
    suggestions = semantic_result.get("suggestions") or []

    if not suggestions:
        return None

    return {
        "answer": CLARIFICATION_ANSWER,
        "source": None,
        "category": CLARIFICATION_CATEGORY,
        "confidence": semantic_result["confidence"],
        "suggestions": suggestions,
    }


def search_knowledge(
    question: str,
    language: str = "fr",
) -> dict[str, Any]:
    faq_result = knowledge_service.search(question)
    semantic_result = semantic_service.search(question, language)

    candidates = (
        *build_faq_candidates(faq_result, semantic_result),
        build_candidate(
            "procedure",
            procedure_service.search(question),
            procedure_service.minimum_confidence,
        ),
        build_candidate(
            "contact",
            contact_service.search(question),
            contact_service.minimum_confidence,
        ),
        build_candidate(
            "schedule",
            schedule_service.search(question),
            schedule_service.minimum_confidence,
        ),
        build_candidate(
            "document",
            document_service.search(question),
            document_service.minimum_confidence,
        ),
    )

    ranked = rank_candidates(candidates)
    logger.debug("knowledge ranking: %s", explain_ranking(ranked))

    result = select_answer(ranked, faq_result)

    # Aucune source fiable : plutôt qu'un « je ne sais pas », on propose
    # les questions proches trouvées par le sémantique (US-018).
    if result["category"] == UNKNOWN_CATEGORY:
        return build_clarification(semantic_result) or result

    return result

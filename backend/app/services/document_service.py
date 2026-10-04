from difflib import SequenceMatcher
from typing import Any

from backend.app.services.document_loader import (
    load_document_chunks,
)
from backend.app.services.text_matching import normalize_text


DOCUMENT_SYNONYMS = {
    "justifier": {"justifiee", "justification", "justificatif"},
    "harcelement": {"signalement", "victime", "protection"},
    "droits": {"droit", "protection", "recours"},
    "sanctions": {"sanction", "disciplinaire"},
}

DOCUMENT_KEYWORDS = {
    "absence",
    "retard",
    "fraude",
    "plagiat",
    "sanction",
    "discipline",
    "harcelement",
    "discrimination",
    "examen",
    "bibliotheque",
    "handicap",
    "sante",
    "stress",
    "methodologie",
    "revision",
    "reglement",
    "droit",
    "devoir",
}

UNKNOWN_ANSWER = (
    "Je n’ai trouvé aucune information suffisamment fiable "
    "dans les documents pédagogiques disponibles."
)


def calculate_document_score(
    question: str,
    content: str,
) -> float:
    normalized_question = normalize_text(question)
    normalized_content = normalize_text(content)

    question_words = set(normalized_question.split())
    content_words = set(normalized_content.split())

    expanded_question_words = set(question_words)

    for word in question_words:
        expanded_question_words.update(
            DOCUMENT_SYNONYMS.get(word, set())
        )

    common_words = expanded_question_words & content_words

    if not common_words:
        return 0.0

    coverage = len(common_words) / max(1, len(question_words))

    sequence_score = SequenceMatcher(
        None,
        normalized_question,
        normalized_content[:500],
    ).ratio()

    keyword_matches = len(
        expanded_question_words
        & DOCUMENT_KEYWORDS
        & content_words
    )

    score = (
        coverage * 0.70
        + sequence_score * 0.10
        + min(keyword_matches / 2, 1.0) * 0.20
    )

    return min(score, 1.0)


class DocumentService:
    minimum_confidence = 0.55

    def __init__(self) -> None:
        self.chunks = load_document_chunks()

    def search(self, question: str) -> dict[str, Any]:
        best_chunk: dict[str, Any] | None = None
        best_score = 0.0

        for chunk in self.chunks:
            score = calculate_document_score(
                question,
                chunk["content"],
            )

            if score > best_score:
                best_score = score
                best_chunk = chunk

        confidence = round(best_score, 3)

        if (
            best_chunk is None
            or confidence < self.minimum_confidence
        ):
            return {
                "answer": UNKNOWN_ANSWER,
                "source": None,
                "category": "unknown",
                "confidence": confidence,
                "document_id": None,
                "chunk_id": None,
            }

        answer = (
            f"## {best_chunk['title']}\n\n"
            f"{best_chunk['content']}\n\n"
            "_Information issue de documents pédagogiques "
            "historiques 2024-2025 et non officiels._"
        )

        return {
            "answer": answer,
            "source": best_chunk["source"],
            "category": "document",
            "confidence": confidence,
            "document_id": best_chunk["document_id"],
            "chunk_id": best_chunk["id"],
        }


document_service = DocumentService()
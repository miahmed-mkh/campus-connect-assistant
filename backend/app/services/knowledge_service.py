import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


FAQ_PATH = Path(__file__).resolve().parents[2] / "data" / "faq.json"


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())

    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    normalized = re.sub(
        r"[^a-z0-9\s]",
        " ",
        normalized,
    )

    return " ".join(normalized.split())


class KnowledgeService:
    def __init__(self) -> None:
        with FAQ_PATH.open("r", encoding="utf-8") as faq_file:
            self.faq_items: list[dict[str, Any]] = json.load(faq_file)

    def search(self, question: str) -> dict[str, Any]:
        normalized_question = normalize_text(question)

        best_item: dict[str, Any] | None = None
        best_score = 0.0

        for item in self.faq_items:
            for reference_question in item["questions"]:
                score = SequenceMatcher(
                    None,
                    normalized_question,
                    normalize_text(reference_question),
                ).ratio()

                if score > best_score:
                    best_score = score
                    best_item = item

        if best_item is None or best_score < 0.65:
            return {
                "answer": (
                    "Je n’ai pas encore de réponse fiable à cette question. "
                    "Vous pouvez reformuler ou contacter directement "
                    "le service scolarité."
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

"""Réponses en anglais à partir de la FAQ pré-traduite (US-032).

Les traductions sont produites hors ligne par
backend/scripts/knowledge_base/translate_faq.py et versionnées dans
faq_translations_en.json : l'API ne charge aucun modèle de traduction, la
réponse est instantanée et le fichier peut être corrigé à la main.

Seules les réponses de la FAQ sont traduites. Une question anglaise est
presque toujours reconnue par la recherche sémantique, donc dans la FAQ ;
les autres sources (contacts, emploi du temps...) cherchent des mots
français. Pour elles, la réponse reste en français avec une mention.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from backend.app.services.faq_loader import (
    DATA_DIRECTORY,
    load_all_faq_items,
)

logger = logging.getLogger(__name__)

TRANSLATIONS_PATH = (
    DATA_DIRECTORY
    / "knowledge_base"
    / "processed"
    / "faq_translations_en.json"
)

MACHINE_TRANSLATION_NOTE = "_Automatic translation from French._"

FRENCH_ONLY_NOTE = "_This information is only available in French:_"

ENGLISH_FIXED_ANSWERS = {
    "unknown": (
        "I don't have a reliable answer to this question yet. "
        "You can rephrase it or contact the student office directly."
    ),
    "clarification": (
        "I'm not sure I understood correctly. Did you mean:"
    ),
}


class TranslationService:
    def __init__(
        self,
        translations_path: Path = TRANSLATIONS_PATH,
        items_loader: Callable[[], list[dict[str, Any]]] = (
            load_all_faq_items
        ),
    ) -> None:
        self.answers: dict[str, str] = {}
        self.questions: dict[str, str] = {}

        if not translations_path.exists():
            logger.warning(
                "Traductions absentes (%s) : réponses en français",
                translations_path,
            )
            return

        with translations_path.open(encoding="utf-8") as file:
            translations: dict[str, dict[str, str]] = json.load(file)

        # Les résultats de recherche portent le texte, pas l'identifiant :
        # on indexe donc les traductions par texte français.
        for item in items_loader():
            translation = translations.get(item["id"])
            if translation is None:
                continue

            self.answers[item["answer"]] = translation["answer"]
            self.questions[item["questions"][0]] = translation["question"]

    def english_questions(self) -> dict[str, str]:
        return dict(self.questions)

    def translate_question(self, question: str) -> str:
        return self.questions.get(question, question)

    def translate_answer(
        self,
        answer: str,
        category: str,
    ) -> str:
        if category in ENGLISH_FIXED_ANSWERS:
            return ENGLISH_FIXED_ANSWERS[category]

        english = self.answers.get(answer)
        if english is not None:
            return f"{english}\n\n{MACHINE_TRANSLATION_NOTE}"

        return f"{FRENCH_ONLY_NOTE}\n\n{answer}"


translation_service = TranslationService()

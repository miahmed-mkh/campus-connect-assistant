import json
import re
from pathlib import Path

import pytest

from backend.app.services.faq_loader import load_all_faq_items
from backend.app.services.translation_service import (
    ENGLISH_FIXED_ANSWERS,
    FRENCH_ONLY_NOTE,
    MACHINE_TRANSLATION_NOTE,
    TRANSLATIONS_PATH,
    TranslationService,
)

ITEMS = [
    {
        "id": "BIB",
        "questions": ["Quels sont les horaires de la bibliothèque ?"],
        "answer": "La bibliothèque est ouverte de 8h à 20h.",
        "source": "FAQ test",
        "category": "services_campus",
    },
    {
        "id": "SANS",
        "questions": ["Question sans traduction ?"],
        "answer": "Réponse sans traduction.",
        "source": "FAQ test",
        "category": "test",
    },
]


@pytest.fixture
def service(tmp_path: Path) -> TranslationService:
    path = tmp_path / "translations.json"
    path.write_text(
        json.dumps(
            {
                "BIB": {
                    "question": "What are the library opening hours?",
                    "answer": "The library is open from 8 a.m. to 8 p.m.",
                }
            }
        ),
        encoding="utf-8",
    )
    return TranslationService(path, items_loader=lambda: ITEMS)


def test_faq_answer_is_translated_with_note(
    service: TranslationService,
) -> None:
    english = service.translate_answer(
        "La bibliothèque est ouverte de 8h à 20h.",
        "services_campus",
    )

    assert english.startswith("The library is open from 8 a.m. to 8 p.m.")
    assert english.endswith(MACHINE_TRANSLATION_NOTE)


def test_untranslated_answer_stays_french_with_mention(
    service: TranslationService,
) -> None:
    english = service.translate_answer("Réponse sans traduction.", "test")

    assert english.startswith(FRENCH_ONLY_NOTE)
    assert english.endswith("Réponse sans traduction.")


@pytest.mark.parametrize("category", ["unknown", "clarification"])
def test_fixed_messages_have_english_versions(
    service: TranslationService,
    category: str,
) -> None:
    assert (
        service.translate_answer("texte français", category)
        == ENGLISH_FIXED_ANSWERS[category]
    )


def test_questions_are_translated_for_suggestions(
    service: TranslationService,
) -> None:
    assert (
        service.translate_question(
            "Quels sont les horaires de la bibliothèque ?"
        )
        == "What are the library opening hours?"
    )
    assert (
        service.translate_question("Question sans traduction ?")
        == "Question sans traduction ?"
    )


def test_missing_file_keeps_french(tmp_path: Path) -> None:
    service = TranslationService(
        tmp_path / "absent.json",
        items_loader=lambda: ITEMS,
    )

    assert service.english_questions() == {}
    assert service.translate_answer("Réponse.", "test").endswith("Réponse.")


def test_versioned_translations_cover_faq_and_keep_contacts() -> None:
    translations = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    items = load_all_faq_items()

    assert {item["id"] for item in items} <= set(translations)

    contact_pattern = re.compile(
        r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\b\d{2}(?:[ .]\d{2}){4}\b"
    )

    # Le modèle traduisait « bibliotheque@esic.fr » en « library@esic.fr » :
    # aucun e-mail ni téléphone ne doit être modifié.
    for item in items:
        english = translations[item["id"]]["answer"]
        for contact in contact_pattern.findall(item["answer"]):
            assert contact in english, (item["id"], contact)

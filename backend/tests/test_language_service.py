import pytest

from backend.app.services.language_service import detect_language


@pytest.mark.parametrize(
    "question",
    [
        "When does the library open?",
        "How can I get a school certificate?",
        "I lost my student card",
        "where is the cafeteria",
        "Hello",
        "exam dates please",
    ],
)
def test_english_questions_are_detected(question: str) -> None:
    assert detect_language(question) == "en"


@pytest.mark.parametrize(
    "question",
    [
        "À quelle heure ouvre la bibliothèque ?",
        # Sans accents : les mots outils suffisent
        "ou est la bibliotheque",
        "c est quand les exams",
        "je veux faire un stage, je fais comment ?",
        "contact scolarité",
        "Bonjour",
    ],
)
def test_french_questions_are_detected(question: str) -> None:
    assert detect_language(question) == "fr"


@pytest.mark.parametrize("question", ["exams", "stage", "planning", "BU"])
def test_ambiguous_words_default_to_french(question: str) -> None:
    assert detect_language(question) == "fr"

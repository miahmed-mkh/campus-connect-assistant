from backend.app.services.knowledge_service import search_knowledge
from backend.app.services.schedule_loader import SCHEDULE_SOURCE
from backend.app.services.schedule_service import (
    extract_formation,
    extract_group,
    extract_weekday,
    schedule_service,
)


def test_extract_weekday() -> None:
    assert extract_weekday("Quels cours ai-je lundi ?") == "Lundi"
    assert extract_weekday("Planning du vendredi") == "Vendredi"
    assert extract_weekday("Quels sont mes cours ?") is None


def test_extract_group() -> None:
    groups = {
        "B1-A",
        "B3-DATA-1",
        "M1-IA-1",
    }

    assert extract_group(
        "Quels sont les cours de B1-A lundi ?",
        groups,
    ) == "B1-A"

    assert extract_group(
        "Planning du groupe M1-IA-1",
        groups,
    ) == "M1-IA-1"

    assert extract_group(
        "Planning du groupe inconnu",
        groups,
    ) is None


def test_extract_formation() -> None:
    formations = {
        "B1",
        "B3-DATA",
    }

    assert extract_formation(
        "Quand sont les examens de B1 ?",
        formations,
    ) == "B1"

    assert extract_formation(
        "Examens B3-DATA",
        formations,
    ) == "B3-DATA"

    assert extract_formation(
        "Examens de Master 2",
        formations,
    ) is None


def test_search_courses_by_group_and_day() -> None:
    result = schedule_service.search(
        "Quels sont les cours du groupe B1-A lundi ?"
    )

    assert result["category"] == "schedule"
    assert result["schedule_type"] == "courses"
    assert result["confidence"] == 1.0
    assert result["source"] == SCHEDULE_SOURCE
    assert "Cours du Lundi" in result["answer"]
    assert "B1-A" in result["answer"]
    assert "Introduction à la Programmation" in result["answer"]


def test_search_complete_group_schedule() -> None:
    result = schedule_service.search(
        "Quel est l'emploi du temps du groupe B1-A ?"
    )

    assert result["category"] == "schedule"
    assert result["schedule_type"] == "courses"
    assert result["confidence"] == 0.95
    assert "Emploi du temps" in result["answer"]
    assert "Lundi" in result["answer"]
    assert "Vendredi" in result["answer"]


def test_search_subject_schedule() -> None:
    result = schedule_service.search(
        "Où se déroule le cours de Machine Learning Avancé ?"
    )

    assert result["category"] == "schedule"
    assert result["schedule_type"] == "subject"
    assert result["confidence"] >= 0.65
    assert "Machine Learning Avancé" in result["answer"]
    assert "Dr. Julie MOREAU" in result["answer"]
    assert "A003" in result["answer"]
    assert "C002" in result["answer"]


def test_search_exams_by_formation() -> None:
    result = schedule_service.search(
        "Quand sont les examens de B1 ?"
    )

    assert result["category"] == "schedule"
    assert result["schedule_type"] == "exams"
    assert result["confidence"] >= 0.65
    assert "Examens B1" in result["answer"]
    assert "07/01/2025" in result["answer"]
    assert "Introduction à la Programmation" in result["answer"]


def test_search_important_dates() -> None:
    result = schedule_service.search(
        "Quelles sont les dates importantes ?"
    )

    assert result["category"] == "schedule"
    assert result["schedule_type"] == "important_dates"
    assert result["confidence"] >= 0.65
    assert "02/09/2024" in result["answer"]
    assert "Rentrée académique" in result["answer"]


def test_schedule_answer_contains_historical_warning() -> None:
    result = schedule_service.search(
        "Quels sont les cours du groupe B1-A lundi ?"
    )

    assert "historiques 2024-2025" in result["answer"]
    assert "non officielles" in result["answer"]


def test_unknown_group_returns_unknown() -> None:
    result = schedule_service.search(
        "Quels sont les cours du groupe B2-Z lundi ?"
    )

    assert result["category"] == "unknown"
    assert result["schedule_type"] is None
    assert result["confidence"] < 0.65
    assert result["source"] is None


def test_unrelated_question_returns_unknown() -> None:
    result = schedule_service.search(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["category"] == "unknown"
    assert result["schedule_type"] is None
    assert result["source"] is None

def test_global_search_returns_group_schedule() -> None:
    result = search_knowledge(
        "Quels sont les cours du groupe B1-A lundi ?"
    )

    assert result["category"] == "schedule"
    assert result["confidence"] == 1.0
    assert result["source"] is not None
    assert "B1-A" in result["answer"]
    assert "Cours du Lundi" in result["answer"]
    assert "historiques 2024-2025" in result["answer"]


def test_global_search_returns_subject_schedule() -> None:
    result = search_knowledge(
        "Où se déroule le cours de Machine Learning Avancé ?"
    )

    assert result["category"] == "schedule"
    assert result["confidence"] >= 0.65
    assert "Machine Learning Avancé" in result["answer"]
    assert "Dr. Julie MOREAU" in result["answer"]
    assert "A003" in result["answer"]
    assert "C002" in result["answer"]


def test_global_search_returns_exam_schedule() -> None:
    result = search_knowledge(
        "Quand sont les examens de B1 ?"
    )

    assert result["category"] == "schedule"
    assert result["confidence"] >= 0.65
    assert "Examens B1" in result["answer"]
    assert "07/01/2025" in result["answer"]
    assert "historique 2024-2025" in result["answer"]


def test_global_search_returns_important_dates() -> None:
    result = search_knowledge(
        "Quelles sont les dates importantes ?"
    )

    assert result["category"] == "schedule"
    assert result["confidence"] >= 0.65
    assert "Rentrée académique" in result["answer"]
    assert "02/09/2024" in result["answer"]


def test_schedule_integration_preserves_contact_result() -> None:
    result = search_knowledge(
        "Qui enseigne l'algorithmique ?"
    )

    assert result["category"] == "contact"
    assert "bernard" in result["answer"].lower()


def test_schedule_integration_preserves_procedure_result() -> None:
    result = search_knowledge(
        "Quels documents faut-il pour une convention de stage ?"
    )

    assert result["category"] == "procedure"


def test_schedule_integration_preserves_faq_result() -> None:
    result = search_knowledge(
        "Quels sont les horaires de la bibliothèque ?"
    )

    assert result["category"] == "services_campus"
    assert result["confidence"] == 1.0


def test_schedule_integration_preserves_unknown_result() -> None:
    result = search_knowledge(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["category"] == "unknown"
    assert result["confidence"] < 0.65
    assert result["source"] is None
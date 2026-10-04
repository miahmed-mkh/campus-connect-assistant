from backend.app.services.procedure_loader import (
    PROCEDURE_SOURCE,
)
from backend.app.services.procedure_service import (
    format_procedure_answer,
    procedure_references,
    procedure_service,
)


def test_procedure_service_loads_all_procedures() -> None:
    assert len(procedure_service.procedures) == 25


def test_search_administrative_registration() -> None:
    result = procedure_service.search(
        "Comment faire mon inscription administrative ?"
    )

    assert result["procedure_id"] == "PROC001"
    assert result["category"] == "procedure"
    assert result["confidence"] >= 0.65
    assert result["source"] == PROCEDURE_SOURCE
    assert result["answer"] is not None
    assert "Inscription Administrative" in result["answer"]


def test_search_internship_agreement_documents() -> None:
    result = procedure_service.search(
        "Quels documents faut-il pour une convention de stage ?"
    )

    assert result["procedure_id"] == "PROC004"
    assert result["category"] == "procedure"
    assert result["confidence"] >= 0.65
    assert result["source"] == PROCEDURE_SOURCE
    assert result["answer"] is not None


def test_unknown_procedure_returns_fallback() -> None:
    result = procedure_service.search(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["procedure_id"] is None
    assert result["category"] == "unknown"
    assert result["confidence"] < 0.65
    assert result["source"] is None
    assert result["answer"] is None


def test_procedure_references_include_generated_questions() -> None:
    procedure = procedure_service.procedures[0]
    references = procedure_references(procedure)

    assert procedure["titre"] in references
    assert (
        "Quels documents faut-il pour "
        "Inscription Administrative ?"
    ) in references
    assert (
        "Quelles sont les étapes pour "
        "Inscription Administrative ?"
    ) in references


def test_format_procedure_answer() -> None:
    procedure = procedure_service.procedures[0]
    answer = format_procedure_answer(procedure)

    assert "## Inscription Administrative" in answer
    assert "**Prérequis :**" in answer
    assert "**Documents nécessaires :**" in answer
    assert "**Étapes :**" in answer
    assert "**Contacts :**" in answer

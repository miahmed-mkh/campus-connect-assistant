from backend.app.services.document_service import (
    
    document_service,
)


def test_document_service_loads_chunks() -> None:
    assert len(document_service.chunks) >= 100


def test_search_plagiarism_sanctions() -> None:
    result = document_service.search(
        "Quelles sont les sanctions en cas de plagiat ?"
    )

    assert result["category"] == "document"
    assert result["document_id"] == "reglement_interieur"
    assert result["confidence"] >= 0.55
    assert result["source"] is not None
    assert "2024-2025" in result["answer"]
    assert "non officiels" in result["answer"]


def test_search_absence_justification() -> None:
    result = document_service.search(
        "Comment justifier une absence ?"
    )

    assert result["category"] == "document"
    assert result["document_id"] == "reglement_interieur"
    assert result["confidence"] >= 0.55
    assert "absence" in result["answer"].lower()


def test_search_harassment_rights() -> None:
    result = document_service.search(
        "Quels sont mes droits en cas de harcèlement ?"
    )

    assert result["category"] == "document"
    assert result["document_id"] == "reglement_interieur"
    assert result["confidence"] >= 0.55
    assert "harcèlement" in result["answer"].lower()


def test_document_result_contains_chunk_identifier() -> None:
    result = document_service.search(
        "Quelles sont les sanctions en cas de plagiat ?"
    )

    assert result["chunk_id"] is not None
    assert result["chunk_id"].startswith(
        "reglement_interieur-"
    )


def test_unknown_document_question_returns_fallback() -> None:
    result = document_service.search(
        "Comment réserver un hélicoptère sur le campus ?"
    )

    assert result["category"] == "unknown"
    assert result["document_id"] is None
    assert result["chunk_id"] is None
    assert result["source"] is None
    assert result["confidence"] < 0.55
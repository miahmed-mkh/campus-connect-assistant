from backend.app.services.document_loader import (
    
    DOCUMENT_SOURCE,
    load_document_chunks,
    split_into_chunks,
)


def test_document_loader_loads_expected_documents() -> None:
    chunks = load_document_chunks()

    document_ids = {
        chunk["document_id"]
        for chunk in chunks
    }

    assert document_ids == {
        "guide_etudiant",
        "reglement_interieur",
    }


def test_document_loader_generates_unique_identifiers() -> None:
    chunks = load_document_chunks()
    identifiers = tuple(chunk["id"] for chunk in chunks)

    assert len(identifiers) == len(set(identifiers))


def test_document_loader_adds_historical_metadata() -> None:
    chunks = load_document_chunks()

    assert chunks
    assert all(
        chunk["source"] == DOCUMENT_SOURCE
        for chunk in chunks
    )
    assert all(
        chunk["academic_year"] == "2024-2025"
        for chunk in chunks
    )
    assert all(
        chunk["official"] is False
        for chunk in chunks
    )


def test_document_loader_produces_non_empty_chunks() -> None:
    chunks = load_document_chunks()

    assert len(chunks) >= 100
    assert all(chunk["content"].strip() for chunk in chunks)


def test_document_loader_contains_regulation_topics() -> None:
    chunks = load_document_chunks()

    regulation_text = " ".join(
        chunk["content"].lower()
        for chunk in chunks
        if chunk["document_id"] == "reglement_interieur"
    )

    assert "fraude" in regulation_text
    assert "plagiat" in regulation_text
    assert "sanction" in regulation_text
    assert "absence" in regulation_text


def test_split_into_chunks_preserves_content() -> None:
    text = "Premier paragraphe.\n\nDeuxième paragraphe."
    chunks = split_into_chunks(text, maximum_characters=25)

    assert chunks == [
        "Premier paragraphe.",
        "Deuxième paragraphe.",
    ]
from backend.app.services.faq_loader import (
    load_all_faq_items,
    load_expanded_faq,
    load_legacy_faq,
)


def test_load_legacy_faq() -> None:
    items = load_legacy_faq()

    assert len(items) == 7

    for item in items:
        assert item["id"]
        assert item["questions"]
        assert item["answer"]
        assert item["category"]


def test_load_expanded_faq() -> None:
    items = load_expanded_faq()

    assert len(items) == 152

    for item in items:
        assert item["id"]
        assert item["questions"]
        assert item["answer"]
        assert item["category"]
        assert item["source"] == (
            "FAQ complète ESIC — données pédagogiques 2024-2025"
        )


def test_load_all_faq_items() -> None:
    items = load_all_faq_items()

    assert len(items) == 159


def test_all_faq_identifiers_are_unique() -> None:
    items = load_all_faq_items()

    identifiers = [
        item["id"]
        for item in items
    ]

    assert len(identifiers) == len(set(identifiers))


def test_expanded_faq_questions_include_tags() -> None:
    items = load_expanded_faq()

    library_item = next(
        item
        for item in items
        if item["id"] == "SVC001"
    )

    assert (
        "Quels sont les horaires de la bibliothèque ?"
        in library_item["questions"]
    )
    assert len(library_item["questions"]) > 1
    assert library_item["category"] == "services_campus"
from backend.app.services.contact_loader import (
    CONTACT_SECTIONS,
    CONTACT_SOURCE,
    load_contacts,
)


def test_contact_loader_returns_all_contacts() -> None:
    contacts = load_contacts()

    assert len(contacts) == 72


def test_contact_loader_generates_unique_identifiers() -> None:
    contacts = load_contacts()
    contact_ids = [contact["id"] for contact in contacts]

    assert len(contact_ids) == len(set(contact_ids))


def test_contact_loader_loads_all_expected_sections() -> None:
    contacts = load_contacts()
    loaded_sections = {
        contact["section"]
        for contact in contacts
    }

    assert loaded_sections == set(CONTACT_SECTIONS)


def test_contact_loader_adds_source_and_section() -> None:
    contacts = load_contacts()

    for contact in contacts:
        assert contact["source"] == CONTACT_SOURCE
        assert contact["section"] in CONTACT_SECTIONS


def test_contact_loader_contains_algorithmics_teacher() -> None:
    contacts = load_contacts()

    teacher = next(
        contact
        for contact in contacts
        if contact["id"] == "E001"
    )

    assert teacher["section"] == "enseignants"
    assert teacher["nom"] == "BERNARD"
    assert "Algorithmique et Structures de Données" in teacher["matieres"]
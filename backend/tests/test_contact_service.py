from backend.app.services.contact_service import contact_service

def test_contact_service_loads_all_contacts() -> None:
    assert len(contact_service.contacts) == 72


def test_search_administrative_service() -> None:
    result = contact_service.search(
        "Comment contacter le service scolarité ?"
    )

    assert result["contact_id"] == "SERVICES_ADMINISTRATIFS-001"
    assert result["category"] == "contact"
    assert result["confidence"] == 1.0
    assert result["source"] is not None
    assert "scolarité" in result["answer"].lower()


def test_search_pedagogical_manager() -> None:
    result = contact_service.search(
        "Quel est l'email du responsable de Bachelor 1 ?"
    )

    assert result["contact_id"] == "RESPONSABLES_PEDAGOGIQUES-001"
    assert result["category"] == "contact"
    assert result["confidence"] == 1.0
    assert "s.martin@esic.fr" in result["answer"].lower()


def test_search_teacher_by_subject() -> None:
    result = contact_service.search(
        "Qui enseigne l'algorithmique ?"
    )

    assert result["contact_id"] == "E001"
    assert result["category"] == "contact"
    assert result["confidence"] >= 0.65
    assert "bernard" in result["answer"].lower()


def test_search_teacher_contact_by_subject() -> None:
    result = contact_service.search(
        "Comment contacter l'enseignant d'algorithmique ?"
    )

    assert result["contact_id"] == "E001"
    assert result["category"] == "contact"
    assert result["confidence"] >= 0.65
    assert result["source"] is not None


def test_search_external_partner() -> None:
    result = contact_service.search(
        "Comment contacter le CROUS de Paris ?"
    )

    assert result["contact_id"] == "PARTENAIRES_EXTERNES-001"
    assert result["category"] == "contact"
    assert result["confidence"] >= 0.65
    assert "crous" in result["answer"].lower()


def test_unknown_contact_returns_fallback() -> None:
    result = contact_service.search(
        "Comment contacter le pilote d'hélicoptère du campus ?"
    )

    assert result["contact_id"] is None
    assert result["category"] == "unknown"
    assert result["confidence"] < 0.65
    assert result["source"] is None
from backend.app.services.procedure_loader import (
    PROCEDURE_SOURCE,
    load_procedure_data,
    load_procedures,
)


def test_load_procedure_data() -> None:
    data = load_procedure_data()

    assert isinstance(data, dict)
    assert "metadata" in data
    assert "procedures" in data
    assert isinstance(data["procedures"], list)


def test_load_all_procedures() -> None:
    procedures = load_procedures()

    assert len(procedures) == 25


def test_procedure_identifiers_are_unique() -> None:
    procedures = load_procedures()

    identifiers = [
        procedure["id"]
        for procedure in procedures
    ]

    assert len(identifiers) == len(set(identifiers))


def test_procedures_have_required_fields() -> None:
    procedures = load_procedures()

    for procedure in procedures:
        assert procedure["id"]
        assert procedure["titre"]
        assert procedure["categorie"]
        assert procedure["description"]
        assert procedure["source"] == PROCEDURE_SOURCE


def test_first_procedure_is_administrative_registration() -> None:
    procedures = load_procedures()

    first_procedure = procedures[0]

    assert first_procedure["id"] == "PROC001"
    assert first_procedure["titre"] == (
        "Inscription Administrative"
    )

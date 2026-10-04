import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIRECTORY = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "knowledge_base"
    / "processed"
)


def load_json(filename: str) -> dict:
    path = PROCESSED_DIRECTORY / filename

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_processed_knowledge_base_files_exist() -> None:
    expected_files = {
        "annuaire_contacts.json",
        "emploi_du_temps.csv",
        "emploi_du_temps.json",
        "faq_complete.json",
        "procedures_esic.json",
    }

    existing_files = {
        path.name
        for path in PROCESSED_DIRECTORY.iterdir()
        if path.is_file()
    }

    assert expected_files <= existing_files


def test_faq_identifiers_are_unique() -> None:
    data = load_json("faq_complete.json")

    questions = [
        question
        for category in data["categories"]
        for question in category["questions"]
    ]

    identifiers = [
        question["id"]
        for question in questions
    ]

    assert len(data["categories"]) == 5
    assert len(questions) == 152
    assert len(identifiers) == len(set(identifiers))


def test_procedure_identifiers_are_unique() -> None:
    data = load_json("procedures_esic.json")
    procedures = data["procedures"]

    identifiers = [
        procedure["id"]
        for procedure in procedures
    ]

    assert len(procedures) == 25
    assert len(identifiers) == len(set(identifiers))


def test_schedule_references_are_valid() -> None:
    data = load_json("emploi_du_temps.json")

    subject_codes = {
        subject["code"]
        for subject in data["matieres"]
    }

    teacher_ids = {
        teacher["id"]
        for teacher in data["enseignants"]
    }

    room_codes = {
        room["code"]
        for room in data["salles"]
    }

    courses = [
        course
        for schedule in data["emploi_du_temps"]
        for course in schedule["cours"]
    ]

    assert len(courses) == 56

    for course in courses:
        assert course["matiere_code"] in subject_codes
        assert course["enseignant"] in teacher_ids
        assert course["salle"] in room_codes


def test_processed_schedule_csv_is_valid_utf8() -> None:
    path = PROCESSED_DIRECTORY / "emploi_du_temps.csv"

    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    expected_columns = {
        "formation",
        "groupe",
        "semestre",
        "jour",
        "heure_debut",
        "heure_fin",
        "matiere_code",
        "matiere_nom",
        "type_cours",
        "enseignant_id",
        "enseignant_nom",
        "salle_code",
        "salle_nom",
    }

    assert rows
    assert expected_columns <= set(rows[0])

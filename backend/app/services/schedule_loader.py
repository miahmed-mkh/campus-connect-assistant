import json
from pathlib import Path
from typing import Any


SCHEDULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "knowledge_base"
    / "processed"
    / "emploi_du_temps.json"
)

SCHEDULE_SOURCE = (
    "Emploi du temps ESIC — données pédagogiques historiques "
    "2024-2025 non officielles"
)


def load_schedule_data() -> dict[str, Any]:
    with SCHEDULE_PATH.open(encoding="utf-8") as schedule_file:
        data: dict[str, Any] = json.load(schedule_file)

    return data


def load_course_slots() -> list[dict[str, Any]]:
    data = load_schedule_data()
    course_slots: list[dict[str, Any]] = []

    for schedule in data["emploi_du_temps"]:
        for course in schedule["cours"]:
            course_slots.append(
                {
                    **course,
                    "formation": schedule["formation"],
                    "groupe": schedule["groupe"],
                    "semestre": schedule["semestre"],
                    "source": SCHEDULE_SOURCE,
                }
            )

    return course_slots


def load_exams() -> list[dict[str, Any]]:
    data = load_schedule_data()
    exams: list[dict[str, Any]] = []

    for exam_session in data["examens"]:
        for exam in exam_session["epreuves"]:
            exams.append(
                {
                    **exam,
                    "formation": exam_session["formation"],
                    "semestre": exam_session["semestre"],
                    "session": exam_session["session"],
                    "source": SCHEDULE_SOURCE,
                }
            )

    return exams


def load_important_dates() -> list[dict[str, Any]]:
    data = load_schedule_data()

    return [
        {
            **important_date,
            "source": SCHEDULE_SOURCE,
        }
        for important_date in data["dates_importantes"]
    ]


def load_subjects() -> list[dict[str, Any]]:
    data = load_schedule_data()

    return [
        {
            **subject,
            "source": SCHEDULE_SOURCE,
        }
        for subject in data["matieres"]
    ]


def load_rooms() -> list[dict[str, Any]]:
    data = load_schedule_data()

    return [
        {
            **room,
            "source": SCHEDULE_SOURCE,
        }
        for room in data["salles"]
    ]


def load_schedule_teachers() -> list[dict[str, Any]]:
    data = load_schedule_data()

    return [
        {
            **teacher,
            "source": SCHEDULE_SOURCE,
        }
        for teacher in data["enseignants"]
    ]
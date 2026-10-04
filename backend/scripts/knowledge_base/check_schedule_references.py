import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

SCHEDULE_PATH = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "knowledge_base"
    / "processed"
    / "emploi_du_temps.json"
)


def load_schedule_data() -> dict:
    with SCHEDULE_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    data = load_schedule_data()

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

    missing_subjects: set[str] = set()
    missing_teachers: set[str] = set()
    missing_rooms: set[str] = set()

    total_schedules = 0
    total_courses = 0

    for schedule in data["emploi_du_temps"]:
        total_schedules += 1

        for course in schedule["cours"]:
            total_courses += 1

            subject_code = course.get("matiere_code")
            teacher_id = course.get("enseignant")
            room_code = course.get("salle")

            if subject_code not in subject_codes:
                missing_subjects.add(str(subject_code))

            if teacher_id not in teacher_ids:
                missing_teachers.add(str(teacher_id))

            if room_code not in room_codes:
                missing_rooms.add(str(room_code))

    print(f"Fichier : {SCHEDULE_PATH}")
    print(f"Emplois du temps : {total_schedules}")
    print(f"Créneaux contrôlés : {total_courses}")
    print(
        "Références matières manquantes :",
        sorted(missing_subjects),
    )
    print(
        "Références enseignants manquantes :",
        sorted(missing_teachers),
    )
    print(
        "Références salles manquantes :",
        sorted(missing_rooms),
    )

    has_errors = any(
        (
            missing_subjects,
            missing_teachers,
            missing_rooms,
        )
    )

    if has_errors:
        print("Résultat : références internes invalides")
        return 1

    print("Résultat : toutes les références internes sont valides")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

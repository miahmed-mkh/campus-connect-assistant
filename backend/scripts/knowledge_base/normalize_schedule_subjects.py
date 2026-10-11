import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIRECTORY = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "knowledge_base"
    / "processed"
)

JSON_PATH = DATA_DIRECTORY / "emploi_du_temps.json"
CSV_PATH = DATA_DIRECTORY / "emploi_du_temps.csv"


def load_json_data() -> dict:
    with JSON_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def load_csv_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def build_subjects_from_csv(
    rows: list[dict[str, str]],
) -> dict[str, dict]:
    subjects: dict[str, dict] = {}

    for row in rows:
        code = row["matiere_code"].strip()

        if not code or code in subjects:
            continue

        subjects[code] = {
            "code": code,
            "nom": row["matiere_nom"].strip(),
            "type": None,
            "ects": None,
            "heures_totales": None,
            "formation": row["formation"].strip(),
            "semestre": row["semestre"].strip(),
        }

    return subjects


def main() -> None:
    data = load_json_data()
    csv_rows = load_csv_rows()
    csv_subjects = build_subjects_from_csv(csv_rows)

    declared_codes = {
        subject["code"]
        for subject in data["matieres"]
    }

    used_codes = {
        course["matiere_code"]
        for schedule in data["emploi_du_temps"]
        for course in schedule["cours"]
    }

    missing_codes = sorted(used_codes - declared_codes)

    missing_from_csv = [
        code
        for code in missing_codes
        if code not in csv_subjects
    ]

    if missing_from_csv:
        raise ValueError(
            "Matières introuvables dans le CSV : "
            + ", ".join(missing_from_csv)
        )

    generated_subjects = [
        csv_subjects[code]
        for code in missing_codes
    ]

    data["matieres"].extend(generated_subjects)
    data["matieres"].sort(key=lambda subject: subject["code"])

    JSON_PATH.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Matières déjà déclarées : {len(declared_codes)}")
    print(f"Matières ajoutées : {len(generated_subjects)}")
    print(f"Total des matières : {len(data['matieres'])}")
    print("Fichier traité mis à jour :", JSON_PATH)


if __name__ == "__main__":
    main()

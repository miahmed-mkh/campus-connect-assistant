import json
from pathlib import Path
from typing import Any


DATA_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "knowledge_base"
    / "processed"
)

PROCEDURES_PATH = DATA_DIRECTORY / "procedures_esic.json"

PROCEDURE_SOURCE = (
    "Procédures ESIC — données pédagogiques 2024-2025"
)


def load_procedure_data() -> dict[str, Any]:
    with PROCEDURES_PATH.open(
        "r",
        encoding="utf-8",
    ) as procedure_file:
        data = json.load(procedure_file)

    if not isinstance(data, dict):
        raise ValueError(
            "Le fichier des procédures doit contenir un objet JSON."
        )

    procedures = data.get("procedures")

    if not isinstance(procedures, list):
        raise ValueError(
            "La clé 'procedures' doit contenir une liste."
        )

    return data


def load_procedures() -> list[dict[str, Any]]:
    data = load_procedure_data()
    procedures = data["procedures"]

    normalized_procedures: list[dict[str, Any]] = []

    for procedure in procedures:
        required_fields = {
            "id",
            "titre",
            "categorie",
            "description",
        }

        missing_fields = required_fields - procedure.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))

            raise ValueError(
                f"Procédure invalide : champs manquants : {missing}"
            )

        normalized_procedures.append(
            {
                **procedure,
                "source": PROCEDURE_SOURCE,
            }
        )

    return normalized_procedures

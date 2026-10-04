import json
from pathlib import Path
from typing import Any


DATA_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "knowledge_base"
    / "processed"
)

CONTACTS_PATH = DATA_DIRECTORY / "annuaire_contacts.json"

CONTACT_SOURCE = (
    "Annuaire ESIC — données pédagogiques historiques "
    "2024-2025 non officielles"
)

CONTACT_SECTIONS = (
    "direction",
    "services_administratifs",
    "services_etudiants",
    "responsables_pedagogiques",
    "enseignants",
    "delegues_etudiants",
    "associations_etudiantes",
    "contacts_urgence",
    "partenaires_externes",
)


def load_contact_data() -> dict[str, Any]:
    with CONTACTS_PATH.open(
        "r",
        encoding="utf-8",
    ) as contact_file:
        data = json.load(contact_file)

    if not isinstance(data, dict):
        raise ValueError(
            "Le fichier de contacts doit contenir un objet JSON."
        )

    metadata = data.get("metadata")

    if not isinstance(metadata, dict):
        raise ValueError(
            "La clé 'metadata' doit contenir un objet."
        )

    for section in CONTACT_SECTIONS:
        entries = data.get(section)

        if not isinstance(entries, list):
            raise ValueError(
                f"La section '{section}' doit contenir une liste."
            )

    return data


def load_contacts() -> list[dict[str, Any]]:
    data = load_contact_data()
    contacts: list[dict[str, Any]] = []

    for section in CONTACT_SECTIONS:
        for position, entry in enumerate(
            data[section],
            start=1,
        ):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Entrée invalide dans la section '{section}'."
                )

            identifier = entry.get("id")

            if not identifier:
                identifier = (
                    f"{section.upper()}-{position:03d}"
                )

            contacts.append(
                {
                    **entry,
                    "id": str(identifier),
                    "section": section,
                    "source": CONTACT_SOURCE,
                }
            )

    return contacts

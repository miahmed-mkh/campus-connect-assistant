from difflib import SequenceMatcher
from typing import Any

from backend.app.services.contact_loader import (
    load_contacts,
)
from backend.app.services.text_matching import normalize_text


CONTACT_CONFIDENCE_THRESHOLD = 0.65


def flatten_contact_values(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(value, (int, float, bool)):
        return [str(value)]

    if isinstance(value, list):
        values: list[str] = []

        for item in value:
            values.extend(flatten_contact_values(item))

        return values

    if isinstance(value, dict):
        values: list[str] = []

        for item in value.values():
            values.extend(flatten_contact_values(item))

        return values

    return []


def contact_display_name(
    contact: dict[str, Any],
) -> str:
    for field in (
        "service",
        "organisme",
        "formation",
        "fonction",
        "nom",
    ):
        value = contact.get(field)

        if value:
            return str(value)

    return contact["id"]


def contact_references(contact: dict[str, Any]) -> list[str]:
    references: list[str] = []

    for value in contact.values():
        references.extend(flatten_contact_values(value))

    section = contact.get("section")

    if section == "enseignants":
        full_name = contact_display_name(contact)
        specialty = contact.get("specialite", "")

        references.extend(
            (
                f"Qui enseigne {specialty} ?",
                f"Comment contacter l'enseignant {full_name} ?",
                f"Quel est l'email de l'enseignant {full_name} ?",
                f"Quelles matières enseigne {full_name} ?",
            )
        )

        for subject in contact.get("matieres", ()):
            references.extend(
                (
                    f"Qui enseigne {subject} ?",
                    f"Quel enseignant donne le cours de {subject} ?",
                    f"Comment contacter l'enseignant de {subject} ?",
                    f"Qui est le professeur de {subject} ?",
                )
            )

    elif section == "responsables_pedagogiques":
        formation = contact.get("formation", "")

        references.extend(
            (
                f"Qui est responsable de {formation} ?",
                f"Comment contacter le responsable de {formation} ?",
                f"Quel est l'email du responsable de {formation} ?",
                f"Quel est le téléphone du responsable de {formation} ?",
            )
        )

    elif section in (
        "services_administratifs",
        "services_etudiants",
    ):
        service = contact.get("service", "")

        references.extend(
            (
                f"Comment contacter le service {service} ?",
                f"Quel est l'email du service {service} ?",
                f"Quel est le téléphone du service {service} ?",
                f"Quels sont les horaires du service {service} ?",
            )
        )

    elif section == "direction":
        function = contact.get("fonction", "")

        references.extend(
            (
                f"Qui est {function} ?",
                f"Comment contacter {function} ?",
                f"Quel est l'email de {function} ?",
            )
        )

    elif section == "delegues_etudiants":
        formation = contact.get("formation", "")

        references.extend(
            (
                f"Qui est le délégué de {formation} ?",
                f"Comment contacter le délégué de {formation} ?",
            )
        )

    elif section == "associations_etudiantes":
        name = contact.get("nom", "")

        references.extend(
            (
                f"Comment contacter {name} ?",
                f"Qui est le président de {name} ?",
            )
        )

    elif section == "contacts_urgence":
        service = contact.get("service", "")

        references.extend(
            (
                f"Quel est le numéro de {service} ?",
                f"Comment contacter {service} ?",
                "Quel numéro appeler en urgence ?",
            )
        )

    elif section == "partenaires_externes":
        organization = contact.get("organisme", "")

        references.extend(
            (
                f"Comment contacter {organization} ?",
                f"Quel est le téléphone de {organization} ?",
                f"Quel est l'email de {organization} ?",
            )
        )

    return list(
        dict.fromkeys(
            reference
            for reference in references
            if reference.strip()
        )
    )

def calculate_contact_similarity(
    normalized_question: str,
    normalized_reference: str,
) -> float:
    if normalized_question == normalized_reference:
        return 1.0

    question_words = set(normalized_question.split())
    reference_words = set(normalized_reference.split())
    common_words = question_words & reference_words

    if len(common_words) < 2:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        normalized_question,
        normalized_reference,
    ).ratio()

    question_coverage = len(common_words) / max(
        1,
        len(question_words),
    )

    reference_coverage = len(common_words) / max(
        1,
        len(reference_words),
    )

    return (
        sequence_score * 0.5
        + question_coverage * 0.3
        + reference_coverage * 0.2
    )


def format_person(
    person: dict[str, Any],
) -> str:
    title = str(person.get("titre", "")).strip()
    first_name = str(person.get("prenom", "")).strip()
    last_name = str(person.get("nom", "")).strip()

    identity = " ".join(
        value
        for value in (
            title,
            first_name,
            last_name,
        )
        if value
    )

    details = [
        identity,
        str(person.get("poste", "")).strip(),
        str(person.get("email", "")).strip(),
        str(person.get("telephone", "")).strip(),
    ]

    return " — ".join(
        value
        for value in details
        if value
    )


def format_contact_answer(
    contact: dict[str, Any],
) -> str:
    display_name = contact_display_name(contact)
    sections = [f"## {display_name}"]

    simple_fields = (
        ("fonction", "Fonction"),
        ("specialite", "Spécialité"),
        ("description", "Description"),
        ("email", "Email"),
        ("telephone", "Téléphone"),
        ("bureau", "Bureau"),
        ("batiment", "Bâtiment"),
        ("localisation", "Localisation"),
        ("horaires", "Horaires"),
        ("horaires_rdv", "Horaires de rendez-vous"),
        ("horaires_bureau", "Permanences"),
        ("disponibilite", "Disponibilité"),
        ("acces", "Accès"),
        ("prise_rdv", "Prise de rendez-vous"),
        ("tarifs", "Tarifs"),
    )

    for field, label in simple_fields:
        value = contact.get(field)

        if value:
            sections.append(
                f"**{label} :** {value}"
            )

    person_fields = (
        ("responsable", "Responsable"),
        ("president", "Président"),
        ("delegue_principal", "Délégué principal"),
        ("delegue_suppleant", "Délégué suppléant"),
        ("medecin", "Médecin"),
        ("assistant", "Assistant"),
        ("contact", "Contact"),
    )

    for field, label in person_fields:
        value = contact.get(field)

        if isinstance(value, dict):
            formatted = format_person(value)

            if formatted:
                sections.append(
                    f"**{label} :** {formatted}"
                )

    list_fields = (
        ("missions", "Missions"),
        ("matieres", "Matières"),
        ("services", "Services proposés"),
        ("consultations", "Consultations"),
        ("installations", "Installations"),
    )

    for field, label in list_fields:
        values = contact.get(field)

        if isinstance(values, list) and values:
            lines = "\n".join(
                f"- {value}"
                for value in values
                if not isinstance(value, dict)
            )

            if lines:
                sections.append(
                    f"**{label} :**\n{lines}"
                )

    team = contact.get("equipe")

    if isinstance(team, list) and team:
        team_lines = [
            f"- {format_person(member)}"
            for member in team
            if isinstance(member, dict)
            and format_person(member)
        ]

        if team_lines:
            sections.append(
                "**Équipe :**\n"
                + "\n".join(team_lines)
            )

    sections.append(
        "**Information :** coordonnées issues de données "
        "pédagogiques historiques 2024-2025 non officielles."
    )

    return "\n\n".join(sections)


class ContactService:
    def __init__(self) -> None:
        self.contacts = load_contacts()

    def search(
        self,
        question: str,
    ) -> dict[str, Any]:
        normalized_question = normalize_text(question)

        best_contact: dict[str, Any] | None = None
        best_score = 0.0

        for contact in self.contacts:
            for reference in contact_references(contact):
                score = calculate_contact_similarity(
                    normalized_question,
                    normalize_text(reference),
                )

                if score > best_score:
                    best_score = score
                    best_contact = contact

        if (
            best_contact is None
            or best_score < CONTACT_CONFIDENCE_THRESHOLD
        ):
            return {
                "answer": None,
                "source": None,
                "category": "unknown",
                "confidence": round(best_score, 3),
                "contact_id": None,
            }

        return {
            "answer": format_contact_answer(best_contact),
            "source": best_contact["source"],
            "category": "contact",
            "confidence": round(best_score, 3),
            "contact_id": best_contact["id"],
        }


contact_service = ContactService()

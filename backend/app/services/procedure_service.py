from difflib import SequenceMatcher
from typing import Any

from backend.app.services.text_matching import normalize_text

from backend.app.services.procedure_loader import (
    load_procedures,
)


PROCEDURE_CONFIDENCE_THRESHOLD = 0.65


def calculate_procedure_similarity(
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


def procedure_references(
    procedure: dict[str, Any],
) -> list[str]:
    title = str(procedure["titre"])

    references = [
        title,
        str(procedure["description"]),
        f"Comment faire la procédure {title} ?",
        f"Comment effectuer {title} ?",
        f"Quelles sont les étapes pour {title} ?",
        f"Quels documents faut-il pour {title} ?",
        f"Quels sont les prérequis pour {title} ?",
        f"Quel est le délai pour {title} ?",
        f"Quel est le coût de {title} ?",
        f"Qui contacter pour {title} ?",
    ]

    references.extend(
        str(value)
        for value in procedure.get("prerequis", [])
    )

    references.extend(
        str(value)
        for value in procedure.get(
            "documents_necessaires",
            [],
        )
    )

    for faq_item in procedure.get("faq", []):
        question = faq_item.get("question")

        if question:
            references.append(str(question))

    return references


def format_procedure_answer(
    procedure: dict[str, Any],
) -> str:
    sections = [
        f"## {procedure['titre']}",
        procedure["description"],
    ]

    duration = procedure.get("duree_estimee")

    if duration:
        sections.append(
            f"**Durée estimée :** {duration}"
        )

    period = procedure.get("periode")

    if period:
        sections.append(
            f"**Période :** {period}"
        )

    prerequisites = procedure.get("prerequis", [])

    if prerequisites:
        prerequisite_lines = "\n".join(
            f"- {value}"
            for value in prerequisites
        )

        sections.append(
            "**Prérequis :**\n"
            f"{prerequisite_lines}"
        )

    documents = procedure.get(
        "documents_necessaires",
        [],
    )

    if documents:
        document_lines = "\n".join(
            f"- {value}"
            for value in documents
        )

        sections.append(
            "**Documents nécessaires :**\n"
            f"{document_lines}"
        )

    steps = procedure.get("etapes", [])

    if steps:
        step_lines = []

        for index, step in enumerate(
            steps,
            start=1,
        ):
            number = step.get("numero", index)
            title = step.get("titre", "Étape")
            description = step.get("description", "")

            line = f"{number}. **{title}**"

            if description:
                line += f" — {description}"

            step_lines.append(line)

        sections.append(
            "**Étapes :**\n"
            + "\n".join(step_lines)
        )

    deadline = procedure.get("delais")

    if deadline:
        sections.append(
            f"**Délais :** {deadline}"
        )

    cost = procedure.get("cout")

    if cost:
        sections.append(
            f"**Coût :** {cost}"
        )

    contacts = procedure.get("contacts", [])

    if contacts:
        contact_lines = []

        for contact in contacts:
            values = [
                str(contact.get("service", "")).strip(),
                str(contact.get("email", "")).strip(),
                str(contact.get("telephone", "")).strip(),
            ]

            contact_line = " — ".join(
                value
                for value in values
                if value
            )

            if contact_line:
                contact_lines.append(
                    f"- {contact_line}"
                )

        if contact_lines:
            sections.append(
                "**Contacts :**\n"
                + "\n".join(contact_lines)
            )

    return "\n\n".join(sections)


class ProcedureService:
    minimum_confidence = PROCEDURE_CONFIDENCE_THRESHOLD

    def __init__(self) -> None:
        self.procedures = load_procedures()

    def search(
        self,
        question: str,
    ) -> dict[str, Any]:
        normalized_question = normalize_text(question)

        best_procedure: dict[str, Any] | None = None
        best_score = 0.0

        for procedure in self.procedures:
            for reference in procedure_references(
                procedure
            ):
                normalized_reference = normalize_text(
                    reference
                )

                score = calculate_procedure_similarity(
                    normalized_question,
                    normalized_reference,
                )

                if score > best_score:
                    best_score = score
                    best_procedure = procedure

        if (
            best_procedure is None
            or best_score
            < PROCEDURE_CONFIDENCE_THRESHOLD
        ):
            return {
                "answer": None,
                "source": None,
                "category": "unknown",
                "confidence": round(best_score, 3),
                "procedure_id": None,
            }

        return {
            "answer": format_procedure_answer(
                best_procedure
            ),
            "source": best_procedure["source"],
            "category": "procedure",
            "confidence": round(best_score, 3),
            "procedure_id": best_procedure["id"],
        }


procedure_service = ProcedureService()

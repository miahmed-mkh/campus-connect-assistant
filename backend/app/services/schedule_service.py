from datetime import datetime
from typing import Any

from backend.app.services.schedule_loader import (
    SCHEDULE_SOURCE,
    load_course_slots,
    load_exams,
    load_important_dates,
)
from backend.app.services.text_matching import normalize_text


WEEKDAYS = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)

SCHEDULE_THRESHOLD = 0.65


def extract_weekday(question: str) -> str | None:
    normalized_question = normalize_text(question)

    for weekday in WEEKDAYS:
        if weekday in normalized_question.split():
            return weekday.capitalize()

    return None


def extract_group(
    question: str,
    groups: set[str],
) -> str | None:
    normalized_question = normalize_text(question)

    for group in sorted(groups, key=len, reverse=True):
        normalized_group = normalize_text(group)

        if normalized_group in normalized_question:
            return group

    return None


def extract_formation(
    question: str,
    formations: set[str],
) -> str | None:
    normalized_question = normalize_text(question)

    for formation in sorted(formations, key=len, reverse=True):
        normalized_formation = normalize_text(formation)

        if normalized_formation in normalized_question:
            return formation

    return None


def format_course_slots(
    slots: list[dict[str, Any]],
    *,
    title: str,
) -> str:
    lines = [
        title,
        "",
        (
            "_Données pédagogiques historiques 2024-2025 "
            "non officielles._"
        ),
        "",
    ]

    sorted_slots = sorted(
        slots,
        key=lambda slot: (
            WEEKDAYS.index(normalize_text(slot["jour"])),
            slot["heure_debut"],
        ),
    )

    for slot in sorted_slots:
        lines.append(
            (
                f'- **{slot["jour"]} '
                f'{slot["heure_debut"]}-{slot["heure_fin"]}** — '
                f'{slot["matiere_nom"]} ({slot["type"]}), '
                f'{slot["enseignant_nom"]}, '
                f'{slot["salle"]} — {slot["salle_nom"]}'
            )
        )

    return "\n".join(lines)


def format_exams(
    exams: list[dict[str, Any]],
    formation: str,
) -> str:
    lines = [
        f"## Examens {formation}",
        "",
        (
            "_Calendrier historique 2024-2025, "
            "non applicable comme calendrier actuel._"
        ),
        "",
    ]

    for exam in sorted(
        exams,
        key=lambda item: (
            item["date"],
            item["heure_debut"],
        ),
    ):
        date = datetime.strptime(
            exam["date"],
            "%Y-%m-%d",
        ).strftime("%d/%m/%Y")

        lines.append(
            (
                f'- **{date} à {exam["heure_debut"]}** — '
                f'{exam["matiere_nom"]}, '
                f'durée {exam["duree"]}, '
                f'salle {exam["salle"]}, '
                f'{exam["type"]}'
            )
        )

    return "\n".join(lines)


def format_important_dates(
    dates: list[dict[str, Any]],
) -> str:
    lines = [
        "## Dates importantes",
        "",
        (
            "_Calendrier historique de l’année académique "
            "2024-2025._"
        ),
        "",
    ]

    for item in sorted(dates, key=lambda entry: entry["date"]):
        date = datetime.strptime(
            item["date"],
            "%Y-%m-%d",
        ).strftime("%d/%m/%Y")

        lines.append(
            (
                f'- **{date}** — {item["evenement"]} '
                f'({item["type"]})'
            )
        )

    return "\n".join(lines)


class ScheduleService:
    minimum_confidence = SCHEDULE_THRESHOLD

    def __init__(self) -> None:
        self.course_slots = load_course_slots()
        self.exams = load_exams()
        self.important_dates = load_important_dates()

        self.groups = {
            slot["groupe"]
            for slot in self.course_slots
        }
        self.formations = {
            slot["formation"]
            for slot in self.course_slots
        } | {
            exam["formation"]
            for exam in self.exams
        }

    def unknown_result(
        self,
        confidence: float = 0.0,
    ) -> dict[str, Any]:
        return {
            "answer": (
                "Je n’ai pas trouvé d’information fiable dans "
                "l’emploi du temps historique 2024-2025."
            ),
            "source": None,
            "category": "unknown",
            "confidence": round(confidence, 3),
            "schedule_type": None,
        }

    def search_course_schedule(
        self,
        question: str,
    ) -> dict[str, Any] | None:
        normalized_question = normalize_text(question)
        group = extract_group(question, self.groups)
        weekday = extract_weekday(question)

        schedule_terms = (
            "cours",
            "emploi du temps",
            "planning",
            "programme",
        )

        if group is None:
            return None

        if not any(
            term in normalized_question
            for term in schedule_terms
        ):
            return None

        slots = [
            slot
            for slot in self.course_slots
            if slot["groupe"] == group
            and (
                weekday is None
                or normalize_text(slot["jour"])
                == normalize_text(weekday)
            )
        ]

        if not slots:
            return None

        if weekday:
            title = f"## Cours du {weekday} — groupe {group}"
            confidence = 1.0
        else:
            title = f"## Emploi du temps — groupe {group}"
            confidence = 0.95

        return {
            "answer": format_course_slots(slots, title=title),
            "source": SCHEDULE_SOURCE,
            "category": "schedule",
            "confidence": confidence,
            "schedule_type": "courses",
        }

    def search_subject(
        self,
        question: str,
    ) -> dict[str, Any] | None:
        normalized_question = normalize_text(question)

        best_subject = ""
        best_slots: list[dict[str, Any]] = []

        subject_names = {
            slot["matiere_nom"]
            for slot in self.course_slots
        }

        for subject_name in subject_names:
            normalized_subject = normalize_text(subject_name)
            subject_words = set(normalized_subject.split())
            question_words = set(normalized_question.split())
            common_words = subject_words & question_words

            significant_words = {
                word
                for word in subject_words
                if len(word) >= 3
            }

            if (
                normalized_subject in normalized_question
                or (
                    significant_words
                    and len(common_words & significant_words)
                    >= min(2, len(significant_words))
                )
            ):
                slots = [
                    slot
                    for slot in self.course_slots
                    if slot["matiere_nom"] == subject_name
                ]

                if len(normalized_subject) > len(
                    normalize_text(best_subject)
                ):
                    best_subject = subject_name
                    best_slots = slots

        if not best_slots:
            return None

        title = f"## {best_subject}"

        return {
            "answer": format_course_slots(
                best_slots,
                title=title,
            ),
            "source": SCHEDULE_SOURCE,
            "category": "schedule",
            "confidence": 0.9,
            "schedule_type": "subject",
        }

    def search_exams(
        self,
        question: str,
    ) -> dict[str, Any] | None:
        normalized_question = normalize_text(question)

        if not any(
            term in normalized_question
            for term in (
                "examen",
                "examens",
                "epreuve",
                "epreuves",
                "partiel",
                "partiels",
            )
        ):
            return None

        formation = extract_formation(
            question,
            {
                exam["formation"]
                for exam in self.exams
            },
        )

        if formation is None:
            return None

        exams = [
            exam
            for exam in self.exams
            if exam["formation"] == formation
        ]

        if not exams:
            return None

        return {
            "answer": format_exams(exams, formation),
            "source": SCHEDULE_SOURCE,
            "category": "schedule",
            "confidence": 0.95,
            "schedule_type": "exams",
        }

    def search_important_dates(
        self,
        question: str,
    ) -> dict[str, Any] | None:
        normalized_question = normalize_text(question)

        terms = (
            "dates importantes",
            "calendrier academique",
            "calendrier scolaire",
            "rentree academique",
            "vacances",
        )

        if not any(
            term in normalized_question
            for term in terms
        ):
            return None

        return {
            "answer": format_important_dates(
                self.important_dates
            ),
            "source": SCHEDULE_SOURCE,
            "category": "schedule",
            "confidence": 0.9,
            "schedule_type": "important_dates",
        }

    def search(self, question: str) -> dict[str, Any]:
        search_methods = (
            self.search_course_schedule,
            self.search_exams,
            self.search_important_dates,
            self.search_subject,
        )

        for search_method in search_methods:
            result = search_method(question)

            if result is not None:
                return result

        return self.unknown_result()


schedule_service = ScheduleService()
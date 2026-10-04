import json
from pathlib import Path
from typing import Any


DATA_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "data"
)

LEGACY_FAQ_PATH = DATA_DIRECTORY / "faq.json"

EXPANDED_FAQ_PATH = (
    DATA_DIRECTORY
    / "knowledge_base"
    / "processed"
    / "faq_complete.json"
)

EXPANDED_FAQ_SOURCE = (
    "FAQ complète ESIC — données pédagogiques 2024-2025"
)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_legacy_faq() -> list[dict[str, Any]]:
    data = load_json(LEGACY_FAQ_PATH)

    if not isinstance(data, list):
        raise ValueError(
            "La FAQ historique doit contenir une liste."
        )

    return data


def load_expanded_faq() -> list[dict[str, Any]]:
    data = load_json(EXPANDED_FAQ_PATH)
    categories = data.get("categories")

    if not isinstance(categories, list):
        raise ValueError(
            "La FAQ complète doit contenir une liste "
            "dans la clé 'categories'."
        )

    items: list[dict[str, Any]] = []

    for category in categories:
        category_id = category["id"]

        for question in category["questions"]:
            tags = question.get("tags", [])

            reference_questions = [
                question["question"],
                *tags,
            ]

            items.append(
                {
                    "id": question["id"],
                    "questions": reference_questions,
                    "answer": question["reponse"],
                    "source": EXPANDED_FAQ_SOURCE,
                    "category": category_id,
                }
            )

    return items


def load_all_faq_items() -> list[dict[str, Any]]:
    legacy_items = load_legacy_faq()
    expanded_items = load_expanded_faq()

    existing_ids = {
        item["id"]
        for item in legacy_items
    }

    unique_expanded_items = [
        item
        for item in expanded_items
        if item["id"] not in existing_ids
    ]

    return [
        *legacy_items,
        *unique_expanded_items,
    ]

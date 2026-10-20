import json
import re

import pytest

from backend.app.services.translation_service import TRANSLATIONS_PATH
from backend.scripts.knowledge_base.translate_faq import (
    FRENCH_RANGE_PATTERN,
    format_range,
    normalize_times,
    protect,
    repair_bold,
    restore,
)


@pytest.mark.parametrize(
    ("translated", "expected"),
    [
        ("Monday-Friday: 8 a.m.-8 p.m.", "Monday-Friday: 8am-8pm"),
        ("from 7:30 a.m. to 9 p.m.", "from 7:30am to 9pm"),
        ("The library (9h-17h)", "The library (9am-5pm)"),
        ("- 12:00 - 14:00 : Lunch", "- 12pm-2pm : Lunch"),
        ("Outdoor sports grounds: 8am-18h", "Outdoor sports grounds: 8am-6pm"),
        ("10.30 p.m.", "10:30pm"),
        # Le point de « a.m. » terminait aussi la phrase
        ("starts at 8:00 a.m. The campus", "starts at 8am. The campus"),
    ],
)
def test_times_use_a_single_english_format(
    translated: str,
    expected: str,
) -> None:
    assert normalize_times(translated) == expected


@pytest.mark.parametrize(
    "duration",
    [
        "24h/24, 7j/7",
        "Plan 10-15h of personal work",
        "Written exams: 1h30 to 4h",
        "Sessions of 1h30, 1-2 times/week",
        "48h loan",
        "I am here",
    ],
)
def test_durations_are_not_converted_to_times(duration: str) -> None:
    assert normalize_times(duration) == duration


def test_contacts_and_ent_labels_are_protected() -> None:
    text = (
        "Écrivez à bibliotheque@esic.fr ou au 01.53.90.15.50 "
        "via 'Scolarité' > 'Ma carte', après l'offre de l'entreprise"
    )

    masked, kept = protect(text)

    assert kept == [
        "bibliotheque@esic.fr",
        "01.53.90.15.50",
        "'Scolarité'",
        "'Ma carte'",
    ]
    # Les élisions ne sont pas prises pour des guillemets
    assert "l'offre de l'entreprise" in masked
    assert restore(masked, kept) == text


def test_time_only_lines_are_protected_before_translation() -> None:
    body = FRENCH_RANGE_PATTERN.sub(format_range, "10h15-12h15")

    masked, kept = protect(body)

    assert masked == "[1]"
    assert kept == ["10:15am-12:15pm"]


def test_broken_bold_is_repaired() -> None:
    assert repair_bold("** Lunch service only:**") == "**Lunch service only:**"


def test_versioned_translations_have_consistent_times() -> None:
    translations = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    text = "\n".join(entry["answer"] for entry in translations.values())

    assert not re.search(r"\b[ap]\.m\.", text)
    assert not re.search(r"\b\d{1,2}h\d{0,2}-\d{1,2}h", text)

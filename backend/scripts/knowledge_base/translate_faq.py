"""Pré-traduit la FAQ en anglais (MarianMT opus-mt-fr-en, hors ligne).

Usage :
    pip install -r backend/requirements-semantic.txt sentencepiece sacremoses
    python -m backend.scripts.knowledge_base.translate_faq

Produit backend/data/knowledge_base/processed/faq_translations_en.json :
{ id: { "question": ..., "answer": ... } }. Le fichier est versionné : il
peut être relu et corrigé à la main, puis l'API le lit sans aucun modèle.

Protections, mesurées sur les 159 réponses :
- e-mails, liens et téléphones : sans elles, « bibliotheque@esic.fr »
  devenait « library@esic.fr », une adresse qui n'existe pas ;
- libellés de l'ENT entre guillemets ('Scolarité' > 'Ma carte') : l'ENT
  réel reste en français ;
- préfixes de liste et indentation, traduits ligne par ligne ;
- gras Markdown : « ** Titre:** » est réparé en « **Titre:** ».
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from backend.app.services.faq_loader import (
    DATA_DIRECTORY,
    load_all_faq_items,
)

MODEL_NAME = "Helsinki-NLP/opus-mt-fr-en"

OUTPUT_PATH = (
    DATA_DIRECTORY
    / "knowledge_base"
    / "processed"
    / "faq_translations_en.json"
)

PROTECTED_PATTERN = re.compile(
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|https?://\S+"
    r"|\b[\w-]+\.esic\.fr\b"
    r"|\b\d{2}(?:[ .]\d{2}){4}\b"
    # Libellé entre guillemets, mais pas l'élision « l'offre avec l'... »
    r"|(?<!\w)'[^'\n]{1,40}'(?!\w)"
    r"|«[^»\n]{1,60}»"
    # Plages horaires déjà converties avant traduction (« 8am-10am ») : le
    # modèle fusionnait sinon « 8h-10h » et « 10h15-12h15 » en une ligne.
    r"|\b\d{1,2}(?::\d{2})?[ap]m-\d{1,2}(?::\d{2})?[ap]m\b"
)
PLACEHOLDER_PATTERN = re.compile(r"\[\d+\]")

LINE_PREFIX_PATTERN = re.compile(r"^(\s*(?:[-*•]\s+|\d+\.\s+)?)(.*)$")
BROKEN_BOLD_PATTERN = re.compile(r"(^|\s)\*\*\s+(?=\S)")
HAS_LETTER_PATTERN = re.compile(r"[A-Za-zÀ-ÿ]")


def protect(text: str) -> tuple[str, list[str]]:
    kept: list[str] = []

    def replace(match: re.Match[str]) -> str:
        kept.append(match.group(0))
        return f"[{len(kept)}]"

    return PROTECTED_PATTERN.sub(replace, text), kept


def restore(text: str, kept: list[str]) -> str:
    for index, value in enumerate(kept, start=1):
        text = text.replace(f"[{index}]", value)
    return text


def repair_bold(text: str) -> str:
    return BROKEN_BOLD_PATTERN.sub(r"\1**", text)


# Horaires : le modèle mélangeait « 8 a.m. », « 9am », « 9h-17h » et
# « 12:00 - 14:00 ». Tout est ramené au style anglais courant « 9am-5pm ».
# Les durées (« 24h/24 », « 10-15h of personal work », « 1h30 à 4h ») ne
# sont pas touchées : seules les plages dont les deux bornes portent « h »
# sont lues comme des heures. Une heure isolée (« 1h30 ») reste ambiguë.
ENGLISH_TIME_PATTERN = re.compile(
    r"\b(\d{1,2})(?:[:.](\d{2}))?\s?([ap])\.?\s?m(\.)?(?![\w])",
    re.IGNORECASE,
)
SENTENCE_START_PATTERN = re.compile(r"\s+[A-Z]")
FRENCH_RANGE_PATTERN = re.compile(
    r"\b(\d{1,2})h(\d{2})?\s?-\s?(\d{1,2})h(\d{2})?(?![\w/])"
)
# « 8am-18h » : début déjà traduit, fin restée au format français
MIXED_RANGE_END_PATTERN = re.compile(
    r"(\d(?:am|pm))\s?-\s?(\d{1,2})h(\d{2})?(?![\w/])"
)
CLOCK_RANGE_PATTERN = re.compile(
    r"\b(\d{1,2}):(\d{2})\s?-\s?(\d{1,2}):(\d{2})\b"
)


def format_clock(hours: str | int, minutes: str | None) -> str:
    hour = int(hours) % 24
    suffix = "am" if hour < 12 else "pm"
    hour = hour % 12 or 12
    return f"{hour}:{minutes}{suffix}" if minutes and minutes != "00" else (
        f"{hour}{suffix}"
    )


def format_english_time(match: re.Match[str]) -> str:
    hours, minutes, period, dot = match.groups()
    hour = int(hours) % 12 + (12 if period.lower() == "p" else 0)

    # « at 8 a.m. The campus... » : le point final de « a.m. » terminait
    # aussi la phrase, on le garde.
    ends_sentence = dot and SENTENCE_START_PATTERN.match(
        match.string,
        match.end(),
    )
    return format_clock(hour, minutes) + ("." if ends_sentence else "")


def format_range(match: re.Match[str]) -> str:
    start_hours, start_minutes, end_hours, end_minutes = match.groups()
    return (
        f"{format_clock(start_hours, start_minutes)}"
        f"-{format_clock(end_hours, end_minutes)}"
    )


def normalize_times(text: str) -> str:
    text = ENGLISH_TIME_PATTERN.sub(format_english_time, text)
    text = FRENCH_RANGE_PATTERN.sub(format_range, text)
    text = CLOCK_RANGE_PATTERN.sub(format_range, text)
    text = MIXED_RANGE_END_PATTERN.sub(
        lambda match: (
            f"{match.group(1)}-{format_clock(match.group(2), match.group(3))}"
        ),
        text,
    )
    # « 8am-8pm » plutôt que « 8am - 8pm » ou « 8am-8 pm »
    return re.sub(r"(\d(?:am|pm))\s?-\s?(?=\d)", r"\1-", text)


class MarianTranslator:
    def __init__(self) -> None:
        from transformers import MarianMTModel, MarianTokenizer

        self.tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
        self.model = MarianMTModel.from_pretrained(MODEL_NAME)

    def translate_lines(self, lines: list[str]) -> list[str]:
        batch = self.tokenizer(lines, return_tensors="pt", padding=True)
        output = self.model.generate(
            **batch,
            num_beams=4,
            max_new_tokens=256,
        )
        return self.tokenizer.batch_decode(
            output,
            skip_special_tokens=True,
        )


def translate_text(translator: MarianTranslator, text: str) -> str:
    lines = text.split("\n")
    jobs: list[tuple[int, str, str, list[str]]] = []

    for index, line in enumerate(lines):
        prefix, body = LINE_PREFIX_PATTERN.match(line).groups()
        body = FRENCH_RANGE_PATTERN.sub(format_range, body)
        masked, kept = protect(body)

        # Une ligne faite seulement d'horaires ou de contacts n'est pas
        # envoyée au modèle.
        if HAS_LETTER_PATTERN.search(PLACEHOLDER_PATTERN.sub("", masked)):
            jobs.append((index, prefix, masked, kept))
        else:
            lines[index] = prefix + body

    if jobs:
        translated = translator.translate_lines(
            [masked for _, _, masked, _ in jobs]
        )
        for (index, prefix, _, kept), english in zip(jobs, translated):
            lines[index] = prefix + normalize_times(
                repair_bold(restore(english, kept))
            )

    return "\n".join(lines)


def translate_items(
    translator: MarianTranslator,
    items: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    translations: dict[str, dict[str, str]] = {}

    for position, item in enumerate(items, start=1):
        translations[item["id"]] = {
            "question": translate_text(translator, item["questions"][0]),
            "answer": translate_text(translator, item["answer"]),
        }
        print(f"[{position}/{len(items)}] {item['id']}", flush=True)

    return translations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        help=(
            "retraduire seulement ces entrées et les fusionner dans le "
            "fichier existant (préserve les corrections manuelles)"
        ),
    )
    arguments = parser.parse_args()

    started = time.perf_counter()
    items = load_all_faq_items()
    translations: dict[str, dict[str, str]] = {}

    if arguments.only:
        translations = json.loads(
            arguments.output.read_text(encoding="utf-8")
        )
        items = [item for item in items if item["id"] in arguments.only]

    translations.update(translate_items(MarianTranslator(), items))

    arguments.output.write_text(
        json.dumps(translations, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{len(items)} entrées traduites en "
        f"{time.perf_counter() - started:.0f} s -> {arguments.output}"
    )


if __name__ == "__main__":
    main()

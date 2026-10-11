import re
import subprocess

from ftfy import fix_text
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

SOURCE_DIRECTORY = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "knowledge_base"
    / "documents"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "knowledge_base"
    / "processed"
    / "documents"
)

DOCUMENTS = (
    "guide_etudiant",
    "presentation_donnees",
    "procedures_administratives_academiques",
    "reglement_interieur",
)


def normalize_extracted_text(text: str) -> str:
    text = fix_text(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x0c", "\n\f\n")

    lines = tuple(
        re.sub(r"[ \t]+$", "", line)
        for line in text.splitlines()
    )

    text = "\n".join(lines)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip() + "\n"


def extract_document(name: str) -> Path:
    source_path = SOURCE_DIRECTORY / f"{name}.pdf"
    output_path = OUTPUT_DIRECTORY / f"{name}.txt"

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Document PDF introuvable : {source_path}"
        )

    process = subprocess.run(
        (
            "pdftotext",
            "-layout",
            "-enc",
            "UTF-8",
            str(source_path),
            "-",
        ),
        check=True,
        capture_output=True,
    )

    extracted_text = None

    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            extracted_text = process.stdout.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if extracted_text is None:
        raise UnicodeError(
            f"Encodage illisible pour le document : {source_path}"
        )

    output_path.write_text(
        normalize_extracted_text(extracted_text),
        encoding="utf-8",
        newline="\n",
    )

    return output_path


def main() -> int:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    for document in DOCUMENTS:
        output_path = extract_document(document)
        print(f"Document extrait : {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCUMENT_DIRECTORY = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "knowledge_base"
    / "processed"
    / "documents"
)

DOCUMENT_SOURCE = (
    "Documents ESIC — données pédagogiques historiques "
    "2024-2025 non officielles"
)

DOCUMENTS = {
    "guide_etudiant": {
        "title": "Guide de l'étudiant ESIC",
        "filename": "guide_etudiant.txt",
    },
    "reglement_interieur": {
        "title": "Règlement intérieur ESIC",
        "filename": "reglement_interieur.txt",
    },
}


def split_into_chunks(
    text: str,
    *,
    maximum_characters: int = 1800,
) -> list[str]:
    paragraphs = tuple(
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    )

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)

        if current_parts and (
            current_length + paragraph_length + 2
            > maximum_characters
        ):
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_length = 0

        current_parts.append(paragraph)
        current_length += paragraph_length + 2

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


def load_document_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for document_id, configuration in DOCUMENTS.items():
        path = DOCUMENT_DIRECTORY / configuration["filename"]

        if not path.is_file():
            raise FileNotFoundError(
                f"Document extrait introuvable : {path}"
            )

        text = path.read_text(encoding="utf-8")

        for position, content in enumerate(
            split_into_chunks(text),
            start=1,
        ):
            chunks.append(
                {
                    "id": f"{document_id}-{position:04d}",
                    "document_id": document_id,
                    "title": configuration["title"],
                    "position": position,
                    "content": content,
                    "source": DOCUMENT_SOURCE,
                    "academic_year": "2024-2025",
                    "official": False,
                }
            )

    return chunks
from typing import Any, Sequence

import numpy as np
import pytest

from backend.app.services import knowledge_service as knowledge_module
from backend.app.services import semantic_service as semantic_module
from backend.app.services.semantic_service import (
    SemanticSearchService,
    is_semantic_reference,
)
from backend.app.services.text_matching import normalize_text


FAKE_ITEMS = [
    {
        "id": "BIB",
        "questions": [
            "Quels sont les horaires de la bibliothèque ?",
            "bibliothèque",
        ],
        "answer": "La bibliothèque est ouverte de 8h à 20h.",
        "source": "FAQ test",
        "category": "services_campus",
    },
    {
        "id": "SCO",
        "questions": [
            "Quels sont les horaires de la scolarité ?",
            "Quand la scolarité est-elle ouverte ?",
        ],
        "answer": "La scolarité est ouverte de 9h à 17h.",
        "source": "FAQ test",
        "category": "service_campus",
    },
]


class BagOfWordsEncoder:
    """Encodeur simulé : un vecteur par mot connu, sans modèle réel."""

    def __init__(self) -> None:
        self.vocabulary: dict[str, int] = {}
        self.encoded_texts: list[str] = []

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        self.encoded_texts.extend(texts)
        rows = []

        for text in texts:
            vector = np.zeros(64, dtype=np.float32)
            for word in normalize_text(text).split():
                index = self.vocabulary.setdefault(
                    word,
                    len(self.vocabulary),
                )
                vector[index % 64] += 1.0
            rows.append(vector)

        return np.stack(rows)


def build_service(
    encoder: BagOfWordsEncoder | None = None,
    enabled: bool = True,
) -> SemanticSearchService:
    encoder = encoder or BagOfWordsEncoder()

    return SemanticSearchService(
        enabled=enabled,
        encoder_factory=lambda: encoder,
        items_loader=lambda: FAKE_ITEMS,
    )


def test_disabled_service_never_loads_the_model() -> None:
    def fail() -> BagOfWordsEncoder:
        raise AssertionError("le modèle ne doit pas être chargé")

    service = SemanticSearchService(
        enabled=False,
        encoder_factory=fail,
        items_loader=lambda: FAKE_ITEMS,
    )

    assert service.warm_up() is False
    assert service.is_ready is False
    assert service.search("bibliothèque")["category"] == "unknown"


def test_search_before_warm_up_returns_unknown() -> None:
    result = build_service().search(
        "Quels sont les horaires de la bibliothèque ?"
    )

    assert result["category"] == "unknown"
    assert result["answer"] is None
    assert result["confidence"] == 0.0


def test_short_tags_are_not_indexed() -> None:
    assert is_semantic_reference(0, "Bonjour") is True
    assert is_semantic_reference(1, "bibliothèque") is False
    assert is_semantic_reference(1, "travail en équipe") is True

    encoder = BagOfWordsEncoder()
    service = build_service(encoder)
    service.warm_up()

    assert "bibliothèque" not in service.reference_texts
    assert len(service.reference_texts) == 3


def test_close_question_returns_matching_answer() -> None:
    service = build_service()
    assert service.warm_up() is True

    result = service.search(
        "horaires de la bibliothèque ?"
    )

    assert result["category"] == "services_campus"
    assert result["answer"] == FAKE_ITEMS[0]["answer"]
    assert result["source"] == "FAQ test"
    assert result["confidence"] >= service.minimum_confidence
    assert result["matched_question"] == FAKE_ITEMS[0]["questions"][0]


def test_distant_question_returns_unknown_with_score() -> None:
    service = build_service()
    service.warm_up()

    result = service.search("réserver un hélicoptère")

    assert result["category"] == "unknown"
    assert result["answer"] is None
    assert result["confidence"] < service.minimum_confidence


def test_model_failure_falls_back_without_retrying() -> None:
    calls = []

    def broken() -> BagOfWordsEncoder:
        calls.append(1)
        raise OSError("modèle introuvable")

    service = SemanticSearchService(
        enabled=True,
        encoder_factory=broken,
        items_loader=lambda: FAKE_ITEMS,
    )

    assert service.warm_up() is False
    assert service.warm_up() is False
    assert len(calls) == 1
    assert service.search("bibliothèque")["category"] == "unknown"


def test_warm_up_is_skipped_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        semantic_module,
        "semantic_service",
        build_service(enabled=False),
    )

    assert semantic_module.start_semantic_warm_up() is None


class FixedSemanticService:
    minimum_confidence = 0.7

    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result

    def search(self, question: str) -> dict[str, Any]:
        return self.result


def test_confident_semantic_answer_replaces_lexical_faq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "À quelle heure ouvre la bibliothèque ?"

    # Sans sémantique, le recouvrement de mots choisit la scolarité
    lexical = knowledge_module.search_knowledge(question)
    assert "scolarité" in lexical["answer"]

    monkeypatch.setattr(
        knowledge_module,
        "semantic_service",
        FixedSemanticService(
            {
                "answer": "La bibliothèque est ouverte de 8h à 20h.",
                "source": "FAQ test",
                "category": "services_campus",
                "confidence": 0.845,
            }
        ),
    )

    result = knowledge_module.search_knowledge(question)

    assert result["answer"] == "La bibliothèque est ouverte de 8h à 20h."
    assert result["category"] == "services_campus"
    assert result["confidence"] == 0.845


def test_exact_lexical_match_is_kept_over_semantic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « contact scolarité » figure tel quel dans la FAQ : le sémantique,
    # moins confiant, ne doit pas le faire perdre face aux documents.
    expected = knowledge_module.search_knowledge("contact scolarité")
    assert expected["category"] == "contact"

    monkeypatch.setattr(
        knowledge_module,
        "semantic_service",
        FixedSemanticService(
            {
                "answer": "Autre réponse",
                "source": "FAQ test",
                "category": "contact",
                "confidence": 0.764,
            }
        ),
    )

    assert knowledge_module.search_knowledge("contact scolarité") == expected


def test_unconfident_semantic_keeps_lexical_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "Quels sont les horaires de la scolarité ?"
    expected = knowledge_module.search_knowledge(question)

    monkeypatch.setattr(
        knowledge_module,
        "semantic_service",
        FixedSemanticService(
            {
                "answer": None,
                "source": None,
                "category": "unknown",
                "confidence": 0.4,
            }
        ),
    )

    assert knowledge_module.search_knowledge(question) == expected

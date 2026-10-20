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
        english_questions_loader=dict,
    )


def test_disabled_service_never_loads_the_model() -> None:
    def fail() -> BagOfWordsEncoder:
        raise AssertionError("le modèle ne doit pas être chargé")

    service = SemanticSearchService(
        enabled=False,
        encoder_factory=fail,
        items_loader=lambda: FAKE_ITEMS,
        english_questions_loader=dict,
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
        english_questions_loader=dict,
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

    def search(self, question: str, language: str = "fr") -> dict[str, Any]:
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


def build_ready_service(
    items: list[dict[str, Any]],
) -> SemanticSearchService:
    service = SemanticSearchService(
        enabled=True,
        encoder_factory=BagOfWordsEncoder,
        items_loader=lambda: items,
        english_questions_loader=dict,
    )
    assert service.warm_up() is True
    return service


def faq_item(item_id: str, question: str, category: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "questions": [question, f"Autre formulation de {item_id} ici"],
        "answer": f"Réponse {item_id}",
        "source": "FAQ test",
        "category": category,
    }


def test_suggestions_skip_greetings_and_duplicates() -> None:
    service = build_ready_service(
        [
            faq_item("BIB", "Horaires de la bibliothèque ?", "services_campus"),
            faq_item("SCO", "Horaires de la scolarité ?", "service_campus"),
            faq_item("SAL", "Bonjour", "salutation"),
        ]
    )
    # Références : BIB, BIB bis, SCO, SCO bis, SAL, SAL bis
    scores = np.array([0.65, 0.40, 0.58, 0.62, 0.69, 0.10])

    # SAL est exclu ; SCO n'apparaît qu'une fois, sous sa question principale
    assert service.build_suggestions(scores) == [
        "Horaires de la bibliothèque ?",
        "Horaires de la scolarité ?",
    ]


def test_suggestions_respect_floor_and_limit() -> None:
    service = build_ready_service(
        [
            faq_item(f"Q{index}", f"Question numéro {index} ?", "test")
            for index in range(5)
        ]
    )

    low_scores = np.full(10, 0.54)
    assert service.build_suggestions(low_scores) == []

    high_scores = np.full(10, 0.6)
    assert len(service.build_suggestions(high_scores)) == 3


def test_unknown_question_with_suggestions_asks_for_clarification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "Comment réserver un hélicoptère sur le campus ?"
    assert knowledge_module.search_knowledge(question)["category"] == "unknown"

    monkeypatch.setattr(
        knowledge_module,
        "semantic_service",
        FixedSemanticService(
            {
                "answer": None,
                "source": None,
                "category": "unknown",
                "confidence": 0.62,
                "suggestions": ["Y a-t-il une navette ?"],
            }
        ),
    )

    result = knowledge_module.search_knowledge(question)

    assert result["category"] == "clarification"
    assert result["answer"] == knowledge_module.CLARIFICATION_ANSWER
    assert result["suggestions"] == ["Y a-t-il une navette ?"]
    assert result["confidence"] == 0.62
    assert result["source"] is None


def test_reliable_answer_is_not_replaced_by_clarification(
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
                "confidence": 0.6,
                "suggestions": ["Autre question ?"],
            }
        ),
    )

    assert knowledge_module.search_knowledge(question) == expected


def test_english_references_are_only_used_for_english_questions() -> None:
    service = SemanticSearchService(
        enabled=True,
        encoder_factory=BagOfWordsEncoder,
        items_loader=lambda: FAKE_ITEMS[:1],
        english_questions_loader=lambda: {
            FAKE_ITEMS[0]["questions"][0]: "What are the library opening hours?"
        },
    )
    service.warm_up()

    english = service.search("library opening hours", "en")
    assert english["answer"] == FAKE_ITEMS[0]["answer"]

    # Une question française ne voit que les références françaises
    french = service.search("library opening hours", "fr")
    assert french["category"] == "unknown"

"""Recherche sémantique dans la FAQ (Sentence-BERT multilingue).

Les questions de référence de la FAQ sont transformées une fois en
vecteurs (embeddings). Une question utilisateur est encodée de la même
façon, puis comparée par similarité cosinus : deux questions formulées
différemment, ou dans une autre langue, restent proches si elles ont le
même sens.

Le modèle est chargé en arrière-plan au démarrage de l'API. Tant qu'il
n'est pas prêt, ou s'il est désactivé ou indisponible, la recherche
renvoie un candidat « unknown » et le moteur lexical prend le relais.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Protocol, Sequence

import numpy as np

from backend.app.core.config import settings
from backend.app.services.faq_loader import load_all_faq_items

logger = logging.getLogger(__name__)

# Seuil de confiance du brief (similarité cosinus > 0.7)
SEMANTIC_CONFIDENCE_THRESHOLD = 0.7

# Les tags de la FAQ complète (« déjeuner », « conseil »...) sont des mots
# isolés : en sémantique ils attirent des questions sans rapport. Seule la
# première référence de chaque entrée est toujours gardée (question
# principale, ou « Bonjour » pour la salutation).
MINIMUM_REFERENCE_WORDS = 3

# Clarification (US-018) : sous le seuil, les questions proches sont
# proposées à l'utilisateur. Plancher mesuré : à 0.5, « réserver un
# hélicoptère » proposait déjà la navette.
SUGGESTION_MINIMUM_CONFIDENCE = 0.55
MAX_SUGGESTIONS = 3

# « il fait beau » est proche de « Bonjour » : proposer une salutation
# n'aide pas l'utilisateur.
SUGGESTION_EXCLUDED_CATEGORIES = {"salutation"}


class Encoder(Protocol):
    def encode(self, texts: Sequence[str]) -> np.ndarray: ...


class SentenceTransformerEncoder:
    def __init__(self, model_name: str) -> None:
        # Import tardif : la dépendance n'est requise que si la recherche
        # sémantique est activée.
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name, device="cpu")

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return self.model.encode(
            list(texts),
            normalize_embeddings=True,
            batch_size=64,
            show_progress_bar=False,
        )


def is_semantic_reference(position: int, text: str) -> bool:
    return position == 0 or len(text.split()) >= MINIMUM_REFERENCE_WORDS


def normalize_rows(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


class SemanticSearchService:
    minimum_confidence = SEMANTIC_CONFIDENCE_THRESHOLD

    def __init__(
        self,
        enabled: bool,
        encoder_factory: Callable[[], Encoder],
        items_loader: Callable[[], list[dict[str, Any]]] = (
            load_all_faq_items
        ),
    ) -> None:
        self.enabled = enabled
        self.encoder_factory = encoder_factory
        self.items_loader = items_loader

        self.encoder: Encoder | None = None
        self.items: list[dict[str, Any]] = []
        self.reference_texts: list[str] = []
        self.reference_owners: list[int] = []
        self.reference_vectors: np.ndarray | None = None

        self.failed = False
        self.lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self.reference_vectors is not None

    def warm_up(self) -> bool:
        if not self.enabled:
            return False

        with self.lock:
            if self.is_ready or self.failed:
                return self.is_ready

            try:
                self.build_index()
            except Exception:
                # Modèle absent, dépendance manquante... : on garde le
                # moteur lexical plutôt que de bloquer l'API.
                self.failed = True
                logger.exception(
                    "Recherche sémantique indisponible, repli sur "
                    "le moteur lexical"
                )
                return False

        logger.info(
            "Index sémantique prêt : %d questions de référence",
            len(self.reference_texts),
        )
        return True

    def build_index(self) -> None:
        items = self.items_loader()
        texts: list[str] = []
        owners: list[int] = []

        for item_index, item in enumerate(items):
            for position, text in enumerate(item["questions"]):
                if is_semantic_reference(position, text):
                    texts.append(text)
                    owners.append(item_index)

        encoder = self.encoder_factory()
        vectors = normalize_rows(encoder.encode(texts))

        self.encoder = encoder
        self.items = items
        self.reference_texts = texts
        self.reference_owners = owners
        self.reference_vectors = vectors

    def search(self, question: str) -> dict[str, Any]:
        if not self.is_ready or self.encoder is None:
            return unknown_result(0.0)

        question_vector = normalize_rows(
            self.encoder.encode([question])
        )[0]
        scores = self.reference_vectors @ question_vector

        best_reference = int(np.argmax(scores))
        best_score = round(float(scores[best_reference]), 3)

        if best_score < self.minimum_confidence:
            return {
                **unknown_result(best_score),
                "suggestions": self.build_suggestions(scores),
            }

        item = self.items[self.reference_owners[best_reference]]

        return {
            "answer": item["answer"],
            "source": item["source"],
            "category": item["category"],
            "confidence": min(best_score, 1.0),
            "matched_question": self.reference_texts[best_reference],
        }

    def build_suggestions(self, scores: np.ndarray) -> list[str]:
        suggestions: list[str] = []
        seen_items: set[int] = set()

        # Une seule suggestion par entrée de la FAQ : sa question
        # principale, qui figure telle quelle dans la FAQ. Un clic la
        # renvoie au chatbot et obtient donc la réponse exacte.
        for reference in np.argsort(-scores):
            if scores[reference] < SUGGESTION_MINIMUM_CONFIDENCE:
                break

            item_index = self.reference_owners[reference]
            item = self.items[item_index]

            if (
                item_index in seen_items
                or item["category"] in SUGGESTION_EXCLUDED_CATEGORIES
            ):
                continue

            seen_items.add(item_index)
            suggestions.append(item["questions"][0])

            if len(suggestions) == MAX_SUGGESTIONS:
                break

        return suggestions


def unknown_result(confidence: float) -> dict[str, Any]:
    return {
        "answer": None,
        "source": None,
        "category": "unknown",
        "confidence": confidence,
    }


def build_default_encoder() -> Encoder:
    return SentenceTransformerEncoder(settings.semantic_model)


semantic_service = SemanticSearchService(
    enabled=settings.semantic_enabled,
    encoder_factory=build_default_encoder,
)


def start_semantic_warm_up() -> threading.Thread | None:
    if not semantic_service.enabled:
        return None

    thread = threading.Thread(
        target=semantic_service.warm_up,
        name="semantic-warm-up",
        daemon=True,
    )
    thread.start()
    return thread

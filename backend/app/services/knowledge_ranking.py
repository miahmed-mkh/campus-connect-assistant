"""Classement unifié et explicable des candidats de réponse.

Chaque service de connaissances (FAQ, procédures, contacts, emploi du
temps, documents) produit un candidat. Les candidats sont comparés sur
leur marge au-dessus de leur propre seuil, et non sur la confiance
brute, car les seuils diffèrent d'un service à l'autre.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

UNKNOWN_CATEGORY = "unknown"

# En cas d'égalité de marge, la source la plus spécifique gagne.
SERVICE_PRIORITY: dict[str, int] = {
    "schedule": 5,
    "contact": 4,
    "procedure": 3,
    "faq": 2,
    "document": 1,
}


@dataclass(frozen=True)
class RankedCandidate:
    service: str
    answer: str | None
    source: str | None
    category: str
    confidence: float
    minimum_confidence: float

    @property
    def accepted(self) -> bool:
        return self.category != UNKNOWN_CATEGORY

    @property
    def margin(self) -> float:
        return round(self.confidence - self.minimum_confidence, 3)

    @property
    def priority(self) -> int:
        return SERVICE_PRIORITY.get(self.service, 0)

    @property
    def reason(self) -> str:
        if self.accepted:
            return (
                f"accepté : confiance {self.confidence:.3f} "
                f">= seuil {self.minimum_confidence:.2f} "
                f"(marge {self.margin:+.3f})"
            )
        return (
            f"rejeté : confiance {self.confidence:.3f} "
            f"< seuil {self.minimum_confidence:.2f}"
        )

    def sort_key(self) -> tuple[bool, float, int]:
        return (self.accepted, self.margin, self.priority)

    def as_result(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "source": self.source,
            "category": self.category,
            "confidence": self.confidence,
        }

    def describe(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "category": self.category,
            "confidence": self.confidence,
            "minimum_confidence": self.minimum_confidence,
            "margin": self.margin,
            "accepted": self.accepted,
            "reason": self.reason,
        }


def build_candidate(
    service: str,
    result: dict[str, Any],
    minimum_confidence: float,
) -> RankedCandidate:
    return RankedCandidate(
        service=service,
        answer=result.get("answer"),
        source=result.get("source"),
        category=result.get("category", UNKNOWN_CATEGORY),
        confidence=float(result.get("confidence", 0.0)),
        minimum_confidence=minimum_confidence,
    )


def rank_candidates(
    candidates: Iterable[RankedCandidate],
) -> list[RankedCandidate]:
    return sorted(
        candidates,
        key=RankedCandidate.sort_key,
        reverse=True,
    )


def explain_ranking(
    ranked: Sequence[RankedCandidate],
) -> dict[str, Any]:
    selected = ranked[0].service if ranked and ranked[0].accepted else None
    return {
        "selected": selected,
        "candidates": [candidate.describe() for candidate in ranked],
    }


def select_answer(
    ranked: Sequence[RankedCandidate],
    fallback: dict[str, Any],
) -> dict[str, Any]:
    if ranked and ranked[0].accepted:
        return ranked[0].as_result()
    return fallback

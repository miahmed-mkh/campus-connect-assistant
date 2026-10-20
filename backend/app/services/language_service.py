"""Détection de la langue d'une question : français ou anglais (US-032).

Les questions sont courtes (« When does the library open? »), un cas où les
détecteurs statistiques génériques se trompent souvent. Une règle simple et
explicable suffit pour deux langues : on compte les mots outils propres à
chacune, les accents comptant pour le français. En cas d'égalité, le
français reste la langue par défaut du campus.
"""

from __future__ import annotations

import re
from typing import Literal

Language = Literal["fr", "en"]

DEFAULT_LANGUAGE: Language = "fr"

ENGLISH_WORDS = {
    "the", "is", "are", "was", "what", "when", "where", "which", "who",
    "why", "how", "can", "could", "do", "does", "did", "i", "my", "me",
    "you", "your", "to", "of", "for", "and", "or", "in", "on", "at", "it",
    "there", "get", "have", "has", "need", "want", "please", "hello", "hi",
    "hey", "thanks", "thank", "open", "opening", "hours", "with", "from",
    "about", "should", "would", "will", "an", "this", "that",
}

FRENCH_WORDS = {
    "le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "est",
    "sont", "quel", "quelle", "quels", "quelles", "quand", "ou", "comment",
    "pourquoi", "qui", "que", "qu", "quoi", "je", "j", "tu", "il", "on",
    "nous", "vous", "mon", "ma", "mes", "ton", "ta", "votre", "vos", "pour",
    "avec", "dans", "sur", "et", "en", "au", "aux", "c", "ce", "cette",
    "faire", "puis", "peux", "veux", "bonjour", "salut", "merci", "horaires",
    "ouvre", "ferme", "y", "a", "pas", "ne",
}

ACCENT_PATTERN = re.compile(r"[àâäçéèêëîïôöùûüÿœæ]", re.IGNORECASE)
WORD_PATTERN = re.compile(r"[a-zàâäçéèêëîïôöùûüÿœæ]+", re.IGNORECASE)


def detect_language(text: str) -> Language:
    words = [word.lower() for word in WORD_PATTERN.findall(text)]

    english_score = sum(word in ENGLISH_WORDS for word in words)
    french_score = sum(word in FRENCH_WORDS for word in words)

    if ACCENT_PATTERN.search(text):
        french_score += 2

    if english_score > french_score:
        return "en"

    return DEFAULT_LANGUAGE

"""Reformulation optionnelle d'une reponse de la base via un LLM local (Ollama).

Le moteur lexical reste la source de verite : le LLM ne fait que reformuler
le passage trouve. En cas de probleme (desactive, lent, erreur, reponse
douteuse), la fonction renvoie None et l'appelant garde la reponse d'origine.
"""

import logging
import re

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Tu es un assistant de campus. Réponds en français, en une ou deux "
    "phrases, uniquement à partir du passage fourni. N'ajoute aucune "
    "information absente du passage. Recopie exactement les horaires, "
    "salles, noms et numéros. Si la réponse n'est pas dans le passage, "
    "réponds exactement : Je n'ai pas cette information."
)

REFUSAL_MARKER = "pas cette information"

CJK_PATTERN = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


def build_user_prompt(question: str, passage: str) -> str:
    return f"Passage : {passage}\n\nQuestion : {question}"


def is_acceptable(text: str) -> bool:
    if not text:
        return False
    if REFUSAL_MARKER in text.lower():
        return False
    if CJK_PATTERN.search(text):
        return False
    return True


def rephrase_answer(question: str, passage: str) -> str | None:
    if not settings.llm_enabled:
        return None
    if len(passage) > settings.llm_max_passage_chars:
        return None



    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, passage)},
        ],
        "stream": False,
        "keep_alive": settings.llm_keep_alive,
        "options": {"temperature": 0},
    }

    try:
        response = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/api/chat",
            json=payload,
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        text = str(response.json()["message"]["content"]).strip()
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        logger.warning("LLM indisponible, repli sur le moteur : %s", type(error).__name__)
        return None

    if not is_acceptable(text):
        logger.warning("Reponse du LLM rejetee, repli sur le moteur")
        return None

    return text

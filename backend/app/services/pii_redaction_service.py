import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionRule:
    pattern: re.Pattern[str]
    replacement: str | Callable[[re.Match[str]], str]


EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    flags=re.IGNORECASE,
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:\+33|0033|0)"
    r"[\s.-]?"
    r"[1-9]"
    r"(?:[\s.-]?\d{2}){4}"
    r"(?!\d)"
)

IPV4_PATTERN = re.compile(
    r"\b"
    r"(?:"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"\."
    r"){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"\b"
)

STUDENT_ID_PATTERN = re.compile(
    r"\b"
    r"(?:num[eé]ro|n[°ºo])"
    r"\s*"
    r"(?:d['’]?\s*)?"
    r"(?:[ée]tudiant|[ée]tudiante)"
    r"\s*"
    r"[:#-]?"
    r"\s*"
    r"[A-Z0-9-]{5,20}"
    r"\b",
    flags=re.IGNORECASE,
)


REDACTION_RULES = (
    RedactionRule(
        pattern=EMAIL_PATTERN,
        replacement="[EMAIL]",
    ),
    RedactionRule(
        pattern=PHONE_PATTERN,
        replacement="[TELEPHONE]",
    ),
    RedactionRule(
        pattern=IPV4_PATTERN,
        replacement="[IP]",
    ),
    RedactionRule(
        pattern=STUDENT_ID_PATTERN,
        replacement="[IDENTIFIANT_ETUDIANT]",
    ),
)


def redact_personal_data(text: str) -> str:
    redacted_text = text

    for rule in REDACTION_RULES:
        redacted_text = rule.pattern.sub(
            rule.replacement,
            redacted_text,
        )

    return redacted_text

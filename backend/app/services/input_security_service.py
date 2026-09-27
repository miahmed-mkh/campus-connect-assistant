import html
import re

from backend.app.schemas.input_security import InputSecurityResult


MAX_MESSAGE_LENGTH = 1000

DANGEROUS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "script_tag",
        re.compile(r"<\s*/?\s*script\b", re.IGNORECASE),
    ),
    (
        "javascript_uri",
        re.compile(r"javascript\s*:", re.IGNORECASE),
    ),
    (
        "html_event_handler",
        re.compile(
            r"\bon[a-z]+\s*=",
            re.IGNORECASE,
        ),
    ),
    (
        "sql_injection",
        re.compile(
            r"\b(?:union\s+select|drop\s+table|delete\s+from)\b",
            re.IGNORECASE,
        ),
    ),
)


def validate_user_input(text: str) -> InputSecurityResult:
    stripped_text = text.strip()

    if not stripped_text:
        return InputSecurityResult(
            is_safe=False,
            reason="empty_message",
            sanitized_text="",
        )

    if len(stripped_text) > MAX_MESSAGE_LENGTH:
        return InputSecurityResult(
            is_safe=False,
            reason="message_too_long",
            sanitized_text="",
        )

    for reason, pattern in DANGEROUS_PATTERNS:
        if pattern.search(stripped_text):
            return InputSecurityResult(
                is_safe=False,
                reason=reason,
                sanitized_text="",
            )

    sanitized_text = html.escape(
        stripped_text,
        quote=True,
    )

    return InputSecurityResult(
        is_safe=True,
        reason=None,
        sanitized_text=sanitized_text,
    )

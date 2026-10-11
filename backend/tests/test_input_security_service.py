import pytest

from backend.app.services.input_security_service import (
    MAX_MESSAGE_LENGTH,
    validate_user_input,
)


@pytest.mark.parametrize(
    ("message", "expected_reason"),
    [
        ("<script>alert(1)</script>", "script_tag"),
        ("<SCRIPT>alert(1)</SCRIPT>", "script_tag"),
        ("javascript:alert(1)", "javascript_uri"),
        ('<img src="x" onerror="alert(1)">', "html_event_handler"),
        ("UNION SELECT password FROM users", "sql_injection"),
        ("DROP TABLE messages", "sql_injection"),
        ("DELETE FROM messages", "sql_injection"),
    ],
)
def test_dangerous_input_is_rejected(
    message: str,
    expected_reason: str,
) -> None:
    result = validate_user_input(message)

    assert result.is_safe is False
    assert result.reason == expected_reason
    assert result.sanitized_text == ""


def test_normal_message_is_accepted() -> None:
    result = validate_user_input(
        "  Bonjour, quand ouvre la bibliothèque ?  "
    )

    assert result.is_safe is True
    assert result.reason is None
    assert (
        result.sanitized_text
        == "Bonjour, quand ouvre la bibliothèque ?"
    )


def test_html_characters_are_escaped() -> None:
    result = validate_user_input(
        "La salle A < la salle B & le bâtiment est \"ouvert\""
    )

    assert result.is_safe is True
    assert result.reason is None
    assert result.sanitized_text == (
        "La salle A &lt; la salle B &amp; "
        "le bâtiment est &quot;ouvert&quot;"
    )


@pytest.mark.parametrize(
    "message",
    [
        "",
        " ",
        "\n\t",
    ],
)
def test_empty_message_is_rejected(message: str) -> None:
    result = validate_user_input(message)

    assert result.is_safe is False
    assert result.reason == "empty_message"
    assert result.sanitized_text == ""


def test_message_at_maximum_length_is_accepted() -> None:
    result = validate_user_input("a" * MAX_MESSAGE_LENGTH)

    assert result.is_safe is True
    assert result.reason is None
    assert len(result.sanitized_text) == MAX_MESSAGE_LENGTH


def test_message_above_maximum_length_is_rejected() -> None:
    result = validate_user_input(
        "a" * (MAX_MESSAGE_LENGTH + 1)
    )

    assert result.is_safe is False
    assert result.reason == "message_too_long"
    assert result.sanitized_text == ""

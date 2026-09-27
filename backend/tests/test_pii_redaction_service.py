import pytest

from backend.app.services.pii_redaction_service import (
    redact_personal_data,
)


@pytest.mark.parametrize(
    ("original_text", "expected_text"),
    [
        (
            "Contactez-moi à etudiant@example.com",
            "Contactez-moi à [EMAIL]",
        ),
        (
            "Écrivez à prenom.nom+campus@esic.fr",
            "Écrivez à [EMAIL]",
        ),
        (
            "Mon téléphone est 06 12 34 56 78",
            "Mon téléphone est [TELEPHONE]",
        ),
        (
            "Appelez le 01.23.45.67.89",
            "Appelez le [TELEPHONE]",
        ),
        (
            "Mon numéro est +33 6 12 34 56 78",
            "Mon numéro est [TELEPHONE]",
        ),
        (
            "Mon IP est 192.168.1.42",
            "Mon IP est [IP]",
        ),
        (
            "Numéro étudiant : ESIC-123456",
            "[IDENTIFIANT_ETUDIANT]",
        ),
        (
            "N° étudiant ABCDE12345",
            "[IDENTIFIANT_ETUDIANT]",
        ),
    ],
)
def test_redact_personal_data(
    original_text: str,
    expected_text: str,
) -> None:
    assert redact_personal_data(original_text) == expected_text


def test_redact_multiple_personal_data() -> None:
    text = (
        "Contact : student@esic.fr, "
        "téléphone 06 12 34 56 78, "
        "IP 10.0.0.25."
    )

    assert redact_personal_data(text) == (
        "Contact : [EMAIL], "
        "téléphone [TELEPHONE], "
        "IP [IP]."
    )


def test_text_without_personal_data_is_unchanged() -> None:
    text = "Quand ouvre la bibliothèque ?"

    assert redact_personal_data(text) == text


def test_empty_text_is_unchanged() -> None:
    assert redact_personal_data("") == ""

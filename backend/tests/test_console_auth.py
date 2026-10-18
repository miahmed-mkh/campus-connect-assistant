import json

import pytest

from backend.app.core import console_auth as auth

FAST = 1000
SECRET = "secret-de-test"


def test_hash_has_expected_format():
    stored = auth.hash_password("mot-de-passe", iterations=FAST)

    assert stored.startswith("pbkdf2_sha256:1000:")
    assert "$" not in stored
    assert "mot-de-passe" not in stored


def test_same_password_gives_different_hashes():
    first = auth.hash_password("identique", iterations=FAST)
    second = auth.hash_password("identique", iterations=FAST)

    assert first != second


def test_verify_password_accepts_good_and_rejects_bad():
    stored = auth.hash_password("bon-mot-de-passe", iterations=FAST)

    assert auth.verify_password("bon-mot-de-passe", stored) is True
    assert auth.verify_password("mauvais", stored) is False
    assert auth.verify_password("", stored) is False


def test_verify_password_rejects_malformed_hashes():
    for value in ("", "abc", "pbkdf2_sha256:x:zz:zz", "md5:1000:00:00", None):
        assert auth.verify_password("x", value) is False


def test_token_roundtrip():
    token = auth.create_token(
        "responsable.si", "responsable", SECRET, 3600, now=1000
    )

    payload = auth.verify_token(token, SECRET, now=1000)

    assert payload == {
        "sub": "responsable.si",
        "role": "responsable",
        "exp": 4600,
    }


def test_token_expires():
    token = auth.create_token("u", "responsable", SECRET, 60, now=1000)

    assert auth.verify_token(token, SECRET, now=1059) is not None
    assert auth.verify_token(token, SECRET, now=1060) is None


def test_token_rejected_with_wrong_secret():
    token = auth.create_token("u", "responsable", SECRET, 3600, now=1000)

    assert auth.verify_token(token, "autre-secret", now=1000) is None


def test_token_rejected_when_role_is_forged():
    token = auth.create_token(
        "etudiant.demo", "etudiant", SECRET, 3600, now=1000
    )
    _, signature = token.split(".")
    forged = {"sub": "etudiant.demo", "role": "responsable", "exp": 4600}
    forged_body = auth._b64encode(
        json.dumps(forged, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    )

    assert auth.verify_token(forged_body + "." + signature, SECRET, now=1000) is None


def test_token_rejects_garbage():
    for value in ("", "abc", "a.b", "a.b.c", "é.é", None):
        assert auth.verify_token(value, SECRET, now=1000) is None


def test_create_token_requires_a_secret():
    with pytest.raises(ValueError):
        auth.create_token("u", "responsable", "", 3600)

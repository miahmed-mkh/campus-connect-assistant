"""Authentification de la console IoT (bibliotheque standard uniquement)."""

import base64
import hashlib
import hmac
import json
import secrets
import time

HASH_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000
SALT_BYTES = 16
SEPARATOR = ":"


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return SEPARATOR.join(
        (HASH_ALGORITHM, str(iterations), salt.hex(), digest.hex())
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored_hash.split(
            SEPARATOR
        )
        if algorithm != HASH_ALGORITHM:
            return False
        iterations = int(iterations_text)
        if iterations < 1:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(candidate, expected)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(body: str, secret: str) -> str:
    mac = hmac.new(
        secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    )
    return _b64encode(mac.digest())


def create_token(
    username: str,
    role: str,
    secret: str,
    ttl_seconds: int,
    now: float | None = None,
) -> str:
    if not secret:
        raise ValueError("Le secret de signature est vide.")

    issued_at = time.time() if now is None else now
    payload = {
        "sub": username,
        "role": role,
        "exp": int(issued_at) + ttl_seconds,
    }
    body = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    )
    return body + "." + _sign(body, secret)


def verify_token(
    token: str | None,
    secret: str,
    now: float | None = None,
) -> dict | None:
    if not secret or not isinstance(token, str):
        return None

    try:
        body, signature = token.split(".")
    except ValueError:
        return None

    expected = _sign(body, secret)
    if not hmac.compare_digest(
        signature.encode("utf-8"), expected.encode("utf-8")
    ):
        return None

    try:
        payload = json.loads(_b64decode(body))
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("sub"), str):
        return None
    if not isinstance(payload.get("role"), str):
        return None
    if not isinstance(payload.get("exp"), int):
        return None

    current = time.time() if now is None else now
    if payload.get("exp") <= current:
        return None

    return payload

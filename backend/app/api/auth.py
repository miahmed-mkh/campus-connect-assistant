from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.iot import DUMMY_HASH, _find_console_account
from backend.app.core.config import settings
from backend.app.core.console_auth import (
    create_token,
    hash_password,
    verify_password,
)
from backend.app.db.database import get_db
from backend.app.models import User
from backend.app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentification"],
)

# Un compte créé depuis l'interface est toujours étudiant.
# Les comptes responsable / intervenant restent ceux de la console (.env).
DEFAULT_ROLE = "etudiant"


def _require_secret() -> None:
    if not settings.console_token_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "auth_disabled",
                "message": "CONSOLE_TOKEN_SECRET n'est pas configuré.",
            },
        )


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "invalid_credentials",
            "message": "Identifiant ou mot de passe incorrect.",
        },
    )


def _auth_response(username: str, role: str, display_name: str) -> AuthResponse:
    token = create_token(
        username,
        role,
        settings.console_token_secret,
        settings.console_token_ttl_seconds,
    )
    return AuthResponse(
        token=token,
        username=username,
        role=role,
        display_name=display_name,
        expires_in=settings.console_token_ttl_seconds,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    database: Session = Depends(get_db),
) -> AuthResponse:
    _require_secret()

    existing = database.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "email_taken",
                "message": "Un compte existe déjà avec cette adresse e-mail.",
            },
        )

    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=DEFAULT_ROLE,
    )
    database.add(user)
    try:
        database.commit()
    except IntegrityError:
        # Deux inscriptions simultanées avec le même e-mail
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "email_taken",
                "message": "Un compte existe déjà avec cette adresse e-mail.",
            },
        )

    return _auth_response(user.email, user.role, user.display_name)


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    payload: LoginRequest,
    database: Session = Depends(get_db),
) -> AuthResponse:
    _require_secret()

    username = payload.username.strip()

    # 1. Comptes créés depuis l'interface : identifiant = e-mail
    if "@" in username:
        email = username.lower()
        user = database.scalar(select(User).where(User.email == email))
        stored_hash = user.password_hash if user else DUMMY_HASH
        password_ok = verify_password(payload.password, stored_hash)

        if user is None or not password_ok:
            raise _invalid_credentials()
        return _auth_response(user.email, user.role, user.display_name)

    # 2. Comptes de la console (responsable, intervenant) définis dans le .env
    account = _find_console_account(username)
    stored_hash = account[2] if account else ""
    password_ok = verify_password(payload.password, stored_hash or DUMMY_HASH)

    if account is None or not stored_hash or not password_ok:
        raise _invalid_credentials()

    role, display_name, _ = account
    return _auth_response(username, role, display_name)

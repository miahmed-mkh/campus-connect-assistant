import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.analytics import require_analytics_key
from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.core.console_auth import create_token, verify_password
from backend.app.schemas.iot import (
    ConsoleLoginRequest,
    ConsoleLoginResponse,
    IotStatus,
    TelemetryAccepted,
    TelemetryPayload,
)
from backend.app.services.iot_service import build_status, record_telemetry

router = APIRouter(
    prefix="/api/iot",
    tags=["IoT"],
)


def require_device_key(
    x_device_key: str | None = Header(
        default=None,
        alias="X-Device-Key",
    ),
) -> None:
    configured_key = settings.iot_device_key

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "iot_disabled",
                "message": "IOT_DEVICE_KEY n'est pas configurée.",
            },
        )

    if not x_device_key or not secrets.compare_digest(
        x_device_key, configured_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_device_key",
                "message": "Clé d'appareil absente ou invalide.",
            },
        )


@router.post(
    "/telemetry",
    response_model=TelemetryAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_device_key)],
)
def post_telemetry(
    payload: TelemetryPayload,
    db: Session = Depends(get_db),
) -> TelemetryAccepted:
    return TelemetryAccepted.model_validate(record_telemetry(db, payload))


@router.get(
    "/status",
    response_model=IotStatus,
    dependencies=[Depends(require_analytics_key)],
)
def get_iot_status(
    db: Session = Depends(get_db),
) -> IotStatus:
    return IotStatus.model_validate(
        build_status(
            db,
            online_threshold_seconds=settings.iot_online_threshold_seconds,
        )
    )



# identifiant, role, nom affiche, nom du reglage contenant le hachage
CONSOLE_ACCOUNTS = (
    ("responsable.si", "responsable", "Responsable du campus", "console_responsable_hash"),
    ("intervenant.maintenance", "intervenant", "Technicien de maintenance", "console_intervenant_hash"),
    ("etudiant.demo", "etudiant", "Étudiant (démo)", "console_etudiant_hash"),
)

# Hachage factice : garde un temps de reponse comparable pour un compte inconnu.
DUMMY_HASH = "pbkdf2_sha256:600000:" + "00" * 16 + ":" + "00" * 32


def _find_console_account(username: str):
    for account_username, role, display_name, hash_setting in CONSOLE_ACCOUNTS:
        if secrets.compare_digest(
            username.encode("utf-8"), account_username.encode("utf-8")
        ):
            return role, display_name, getattr(settings, hash_setting)
    return None


@router.post(
    "/console/login",
    response_model=ConsoleLoginResponse,
)
def console_login(payload: ConsoleLoginRequest) -> ConsoleLoginResponse:
    if not settings.console_token_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "console_disabled",
                "message": "CONSOLE_TOKEN_SECRET n'est pas configuré.",
            },
        )

    account = _find_console_account(payload.username)
    stored_hash = account[2] if account else ""
    password_ok = verify_password(payload.password, stored_hash or DUMMY_HASH)

    if account is None or not stored_hash or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_credentials",
                "message": "Identifiant ou mot de passe incorrect.",
            },
        )

    role, display_name, _ = account
    token = create_token(
        payload.username,
        role,
        settings.console_token_secret,
        settings.console_token_ttl_seconds,
    )
    return ConsoleLoginResponse(
        token=token,
        username=payload.username,
        role=role,
        display_name=display_name,
        expires_in=settings.console_token_ttl_seconds,
    )

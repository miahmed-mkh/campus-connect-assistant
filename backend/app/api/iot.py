import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.analytics import require_analytics_key
from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.schemas.iot import IotStatus, TelemetryAccepted, TelemetryPayload
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

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.iot_reading import IotReading
from backend.app.schemas.iot import TelemetryPayload


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime) -> datetime:
    """Les appareils peuvent envoyer une date sans fuseau : on suppose UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def record_telemetry(db: Session, payload: TelemetryPayload) -> dict:
    received_at = utc_now()

    readings = [
        IotReading(
            device_id=payload.device_id,
            kind=reading.kind,
            value=reading.value,
            unit=reading.unit,
            recorded_at=_ensure_utc(reading.recorded_at),
            received_at=received_at,
        )
        for reading in payload.readings
    ]

    db.add_all(readings)
    db.commit()

    return {
        "device_id": payload.device_id,
        "accepted": len(readings),
        "received_at": received_at,
    }


def build_status(db: Session, online_threshold_seconds: int) -> dict:
    now = utc_now()
    online_since = now - timedelta(seconds=online_threshold_seconds)

    readings_total = db.scalar(select(func.count(IotReading.id))) or 0

    last_seen_rows = db.execute(
        select(
            IotReading.device_id,
            func.max(IotReading.received_at).label("last_seen_at"),
        )
        .group_by(IotReading.device_id)
        .order_by(IotReading.device_id)
    ).all()

    # Dernière mesure par (appareil, type) : DISTINCT ON PostgreSQL
    latest_rows = db.scalars(
        select(IotReading)
        .distinct(IotReading.device_id, IotReading.kind)
        .order_by(
            IotReading.device_id,
            IotReading.kind,
            IotReading.recorded_at.desc(),
        )
    ).all()

    latest_by_device: dict[str, list[dict]] = {}
    for reading in latest_rows:
        latest_by_device.setdefault(reading.device_id, []).append(
            {
                "kind": reading.kind,
                "value": reading.value,
                "unit": reading.unit,
                "recorded_at": reading.recorded_at,
            }
        )

    devices = [
        {
            "device_id": device_id,
            "online": last_seen_at >= online_since,
            "last_seen_at": last_seen_at,
            "latest": latest_by_device.get(device_id, []),
        }
        for device_id, last_seen_at in last_seen_rows
    ]

    return {
        "generated_at": now,
        "online_threshold_seconds": online_threshold_seconds,
        "readings_total": readings_total,
        "devices": devices,
    }

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ReadingKind = Literal["temperature", "humidity", "occupancy", "heartbeat"]


class TelemetryReading(BaseModel):
    kind: ReadingKind
    value: float
    unit: str | None = Field(default=None, max_length=16)
    recorded_at: datetime


class TelemetryPayload(BaseModel):
    device_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
    )
    readings: list[TelemetryReading] = Field(min_length=1, max_length=50)


class TelemetryAccepted(BaseModel):
    device_id: str
    accepted: int
    received_at: datetime


class LatestReading(BaseModel):
    kind: str
    value: float
    unit: str | None
    recorded_at: datetime


class DeviceStatus(BaseModel):
    device_id: str
    online: bool
    last_seen_at: datetime
    latest: list[LatestReading]


class IotStatus(BaseModel):
    generated_at: datetime
    online_threshold_seconds: int
    readings_total: int
    devices: list[DeviceStatus]

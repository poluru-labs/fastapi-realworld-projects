import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

TRACKER_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TrackerStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DECOMMISSIONED = "decommissioned"


class GeofenceStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GeofenceEventType(StrEnum):
    ENTER = "enter"
    EXIT = "exit"


class TrackerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(..., min_length=2, max_length=64, examples=["delivery-van-01"])
    name: str = Field(..., min_length=1, max_length=120)

    @field_validator("key")
    @classmethod
    def normalize_key(cls, key: str) -> str:
        key = key.casefold()
        if not TRACKER_KEY_PATTERN.fullmatch(key):
            raise ValueError("Tracker key must be lowercase words separated by hyphens")
        return key


class TrackerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    status: TrackerStatus
    last_latitude: float | None
    last_longitude: float | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TrackerProvisioned(TrackerRead):
    ingest_token: str = Field(description="Shown once at provision time.")


class LocationIngest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=50_000)
    recorded_at: datetime | None = None
    dedupe_key: str | None = Field(default=None, max_length=128)


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracker_id: int
    latitude: float
    longitude: float
    accuracy_m: float | None
    recorded_at: datetime
    ingested_at: datetime


class LocationIngestResult(BaseModel):
    ping: LocationRead
    geofence_events: list["GeofenceEventRead"]


class LocationTrail(BaseModel):
    tracker_key: str
    window_minutes: int
    points: list[LocationRead]


class GeofenceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    center_latitude: float = Field(..., ge=-90, le=90)
    center_longitude: float = Field(..., ge=-180, le=180)
    radius_m: float = Field(..., gt=0, le=500_000)


class GeofenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    center_latitude: float
    center_longitude: float
    radius_m: float
    status: GeofenceStatus
    created_at: datetime


class GeofenceMonitorAttach(BaseModel):
    geofence_id: int = Field(..., ge=1)


class GeofenceMonitorRead(BaseModel):
    tracker_id: int
    tracker_key: str
    geofence_id: int
    geofence_name: str


class GeofenceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracker_id: int
    geofence_id: int
    event_type: GeofenceEventType
    latitude: float
    longitude: float
    occurred_at: datetime


class TrackerOverview(BaseModel):
    tracker_key: str
    status: TrackerStatus
    total_pings: int
    pings_last_hour: int
    last_seen_at: datetime | None
    last_latitude: float | None
    last_longitude: float | None
    monitored_geofences: int

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AdminKey, DbSession
from app.schemas.telemetry import (
    DEVICE_KEY_PATTERN,
    DeviceCreate,
    DeviceProvisioned,
    DeviceRead,
    DeviceUpdate,
)
from app.services.device_service import DeviceService

router = APIRouter()

DeviceKey = Annotated[
    str,
    Path(pattern=DEVICE_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[DeviceRead],
    summary="List devices",
    description="Admin key required. Includes suspended and decommissioned devices.",
)
async def list_devices(_: AdminKey, session: DbSession) -> list[DeviceRead]:
    return await DeviceService(session).list_devices()


@router.post(
    "",
    response_model=DeviceProvisioned,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a device",
    description=(
        "Admin key required. Returns a one-time **ingest_token** for the firmware. "
        "Only a hash is stored server-side."
    ),
)
async def provision_device(
    _: AdminKey,
    session: DbSession,
    payload: DeviceCreate,
) -> DeviceProvisioned:
    return await DeviceService(session).provision(payload)


@router.get(
    "/{device_key}",
    response_model=DeviceRead,
    summary="Get device metadata",
)
async def get_device(_: AdminKey, session: DbSession, device_key: DeviceKey) -> DeviceRead:
    return await DeviceService(session).get_device(device_key)


@router.patch(
    "/{device_key}",
    response_model=DeviceRead,
    summary="Update device metadata",
)
async def update_device(
    _: AdminKey,
    session: DbSession,
    device_key: DeviceKey,
    payload: DeviceUpdate,
) -> DeviceRead:
    return await DeviceService(session).update_device(device_key, payload)


@router.post(
    "/{device_key}/suspend",
    response_model=DeviceRead,
    summary="Suspend telemetry ingest",
)
async def suspend_device(_: AdminKey, session: DbSession, device_key: DeviceKey) -> DeviceRead:
    return await DeviceService(session).suspend(device_key)


@router.post(
    "/{device_key}/resume",
    response_model=DeviceRead,
    summary="Resume an active device",
)
async def resume_device(_: AdminKey, session: DbSession, device_key: DeviceKey) -> DeviceRead:
    return await DeviceService(session).resume(device_key)


@router.post(
    "/{device_key}/decommission",
    response_model=DeviceRead,
    summary="Permanently retire a device",
)
async def decommission_device(
    _: AdminKey,
    session: DbSession,
    device_key: DeviceKey,
) -> DeviceRead:
    return await DeviceService(session).decommission(device_key)

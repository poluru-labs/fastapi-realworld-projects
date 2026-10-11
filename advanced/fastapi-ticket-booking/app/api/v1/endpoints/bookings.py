from fastapi import APIRouter, Body, status

from app.api.deps import CurrentUser, DbSession, IdempotencyKey
from app.schemas.booking import BookingCreate, BookingRead
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])

_CONFIRM_EXAMPLE = {
    "default": {
        "summary": "Confirm checkout from a hold",
        "value": {"hold_id": 1},
    }
}


@router.get("", response_model=list[BookingRead], summary="List bookings")
async def list_bookings(actor: CurrentUser, session: DbSession) -> list[BookingRead]:
    return await BookingService(session).list_bookings(actor)


@router.get("/{booking_id}", response_model=BookingRead, summary="Get one booking")
async def get_booking(
    booking_id: int,
    actor: CurrentUser,
    session: DbSession,
) -> BookingRead:
    return await BookingService(session).get_booking(actor, booking_id)


@router.post(
    "",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm booking (idempotent)",
    description=(
        "Requires **`Idempotency-Key`**. Converts an active hold into a confirmed booking "
        "and increments `quantity_sold` in the same transaction."
    ),
)
async def confirm_booking(
    actor: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: BookingCreate = Body(openapi_examples=_CONFIRM_EXAMPLE),
) -> BookingRead:
    return await BookingService(session).confirm(
        actor,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post("/{booking_id}/cancel", response_model=BookingRead, summary="Cancel and restock")
async def cancel_booking(
    booking_id: int,
    actor: CurrentUser,
    session: DbSession,
) -> BookingRead:
    return await BookingService(session).cancel(actor, booking_id)

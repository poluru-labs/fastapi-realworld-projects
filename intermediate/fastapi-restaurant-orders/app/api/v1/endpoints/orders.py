from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_order_service
from app.schemas.order import OrderCreate, OrderRead, OrderStatus
from app.schemas.user import UserRead
from app.services.order_service import OrderService

router = APIRouter()

_PLACE_EXAMPLES = {
    "lunch": {
        "summary": "Burger and fries",
        "description": (
            "Each line references an **active**, **available** menu slug. "
            "Prices are snapshotted at order time."
        ),
        "value": {
            "lines": [
                {"menu_item_slug": "classic-burger", "quantity": 1},
                {"menu_item_slug": "fries", "quantity": 2},
            ],
            "note": "No onions please",
        },
    }
}


@router.get(
    "",
    response_model=list[OrderRead],
    summary="List orders",
    description="Customers see their orders. Kitchen admins see every order.",
)
def list_orders(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
    order_status: Annotated[
        OrderStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[OrderRead]:
    return service.list_orders(actor, status=order_status)


@router.get("/{order_id}", response_model=OrderRead, summary="Get one order")
def get_order(
    order_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    return service.get_order(actor, order_id)


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order",
)
def place_order(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
    payload: Annotated[OrderCreate, Body(openapi_examples=_PLACE_EXAMPLES)],
) -> OrderRead:
    return service.place_order(actor, payload)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
    summary="Cancel an order",
    description=(
        "Customers may cancel while status is **placed**. "
        "After that, only kitchen staff may cancel."
    ),
)
def cancel_order(
    order_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    return service.cancel(actor, order_id)


@router.post(
    "/{order_id}/start-preparing",
    response_model=OrderRead,
    summary="Move order to preparing (admin)",
)
def start_preparing(
    order_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    return service.start_preparing(actor, order_id)


@router.post(
    "/{order_id}/mark-ready",
    response_model=OrderRead,
    summary="Mark order ready for pickup (admin)",
)
def mark_ready(
    order_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    return service.mark_ready(actor, order_id)


@router.post(
    "/{order_id}/complete",
    response_model=OrderRead,
    summary="Complete an order",
    description="Customer or kitchen staff when status is **ready**.",
)
def complete_order(
    order_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    return service.complete(actor, order_id)

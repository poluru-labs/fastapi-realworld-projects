from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_order_service
from app.schemas.order import CheckoutCreate, OrderRead, OrderStatus
from app.schemas.user import UserRead
from app.services.order_service import OrderService

router = APIRouter()

_CHECKOUT_EXAMPLES = {
    "default": {
        "summary": "Place order from current cart",
        "description": (
            "Decrements product stock, snapshots line prices, and clears the cart. "
            "Empty cart or insufficient stock returns **409**."
        ),
        "value": {"note": "Leave at front desk if out."},
    }
}


@router.get(
    "",
    response_model=list[OrderRead],
    summary="List orders",
    description=(
        "Signed-in users see their own orders. Platform admins see every order and may "
        "filter with `status`."
    ),
)
def list_orders(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
    order_status: Annotated[
        OrderStatus | None,
        Query(alias="status", description="placed or cancelled."),
    ] = None,
) -> list[OrderRead]:
    return service.list_orders(actor, order_status=order_status)


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
    summary="Checkout (place order)",
)
def checkout(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
    payload: Annotated[CheckoutCreate, Body(openapi_examples=_CHECKOUT_EXAMPLES)],
) -> OrderRead:
    return service.checkout(actor, payload)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
    summary="Cancel an order",
    description=(
        "Buyers cancel their own **placed** orders. Admins may cancel any order. "
        "Stock is returned to each product."
    ),
)
def cancel_order(
    order_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    return service.cancel(actor, order_id)

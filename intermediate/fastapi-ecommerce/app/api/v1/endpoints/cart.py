from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.api.deps import get_cart_service, get_current_user
from app.schemas.cart import CartLineUpsert, CartRead
from app.schemas.user import UserRead
from app.services.cart_service import CartService

router = APIRouter()

_UPSERT_EXAMPLES = {
    "hub": {
        "summary": "Add USB-C hub to cart",
        "description": (
            "Only **active** products with enough **stock** can be added. "
            "Quantity is capped at available stock with **409** when you ask for more."
        ),
        "value": {"product_slug": "usb-c-hub", "quantity": 2},
    }
}


@router.get(
    "",
    response_model=CartRead,
    summary="View your cart",
    description=(
        "Signed-in shoppers only. Inactive products drop out of the cart on read. "
        "Quantities clamp down when stock shrinks."
    ),
)
def get_cart(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartRead:
    return service.get_cart(actor)


@router.put(
    "/lines",
    response_model=CartRead,
    summary="Add or update a cart line",
)
def upsert_cart_line(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CartService, Depends(get_cart_service)],
    payload: Annotated[CartLineUpsert, Body(openapi_examples=_UPSERT_EXAMPLES)],
) -> CartRead:
    return service.upsert_line(actor, payload)


@router.delete(
    "/lines/{product_slug}",
    response_model=CartRead,
    summary="Remove one line from the cart",
)
def remove_cart_line(
    product_slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartRead:
    return service.remove_line(actor, product_slug)


@router.delete(
    "",
    response_model=CartRead,
    status_code=status.HTTP_200_OK,
    summary="Clear the cart",
)
def clear_cart(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartRead:
    return service.clear(actor)

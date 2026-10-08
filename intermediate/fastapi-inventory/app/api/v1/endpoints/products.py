from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_current_user, get_inventory_service
from app.schemas.product import (
    SKU_PATTERN,
    AdjustStock,
    MovementPage,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ReceiveStock,
    SaleStock,
)
from app.schemas.user import UserRead
from app.services.inventory_service import InventoryService

router = APIRouter()

Sku = Annotated[
    str,
    Path(
        pattern=SKU_PATTERN.pattern,
        min_length=1,
        max_length=32,
        description="Product SKU, uppercase letters, digits, and hyphens.",
        examples=["WIDGET-A"],
    ),
]

_CREATE_EXAMPLES = {
    "new_sku": {
        "summary": "New product with starting stock",
        "description": "Platform admin only. Opening stock creates a receive movement.",
        "value": {
            "sku": "LABEL-D",
            "name": "Label roll",
            "description": "Shipping labels",
            "quantity_on_hand": 50,
            "reorder_level": 10,
        },
    },
    "zero_start": {
        "summary": "Catalog entry with no stock yet",
        "value": {
            "sku": "PALLET-E",
            "name": "Empty pallet SKU",
            "reorder_level": 1,
        },
    },
}

_RECEIVE_EXAMPLES = {
    "shipment": {
        "summary": "Receive a shipment",
        "value": {"quantity": 24, "note": "PO-1001"},
    }
}

_SALE_EXAMPLES = {
    "order": {
        "summary": "Ship units to a customer",
        "value": {"quantity": 2, "note": "Order 5501"},
    }
}

_ADJUST_EXAMPLES = {
    "cycle_count": {
        "summary": "Fix count after a cycle count",
        "value": {"delta": -1, "note": "Shelf count mismatch"},
    }
}


@router.get(
    "",
    response_model=list[ProductRead],
    summary="List products",
    description=(
        "Any signed-in user. Inactive products are hidden unless you are a platform admin "
        "and set include_inactive=true. "
        "low_stock=true keeps products at or below reorder_level. "
        "search matches SKU, name, and description, ignoring case."
    ),
)
def list_products(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    low_stock: Annotated[
        bool | None,
        Query(description="true for at or below reorder level, false for above."),
    ] = None,
    include_inactive: Annotated[
        bool,
        Query(description="Platform admin only. Include deactivated SKUs."),
    ] = False,
    search: Annotated[
        str | None,
        Query(min_length=1, max_length=80, description="Case-insensitive text search."),
    ] = None,
) -> list[ProductRead]:
    return service.list_products(
        actor,
        low_stock=low_stock,
        include_inactive=include_inactive,
        search=search,
    )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    description=(
        "Platform admin only. SKU is stored uppercase and must be unique. "
        "quantity_on_hand defaults to 0. A positive starting quantity creates an opening receive "
        "movement in the ledger."
    ),
    responses={
        403: {"description": "Signed in, but not a platform admin."},
        409: {"description": "Duplicate SKU."},
    },
)
def create_product(
    payload: Annotated[ProductCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.create_product(actor, payload)


@router.get(
    "/{sku}",
    response_model=ProductRead,
    summary="Get one product",
    description=(
        "Inactive products return 404 for regular users. Platform admins still see them."
    ),
    responses={404: {"description": "Unknown SKU, or inactive and you are not an admin."}},
)
def get_product(
    sku: Sku,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.get_product(actor, sku)


@router.patch(
    "/{sku}",
    response_model=ProductRead,
    summary="Update catalog fields",
    description=(
        "Platform admin only. Changes name, description, or reorder_level. "
        "SKU and quantity_on_hand are not editable here; use stock movement routes."
    ),
    responses={403: {"description": "Not a platform admin."}},
)
def update_product(
    sku: Sku,
    payload: ProductUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.update_product(actor, sku, payload)


@router.post(
    "/{sku}/deactivate",
    response_model=ProductRead,
    summary="Deactivate a product",
    description=(
        "Platform admin only. Inactive products disappear from the default list and cannot "
        "receive sales or adjustments until activated. Idempotent if already inactive."
    ),
)
def deactivate_product(
    sku: Sku,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.deactivate_product(actor, sku)


@router.post(
    "/{sku}/activate",
    response_model=ProductRead,
    summary="Activate a product",
    description="Platform admin only. Idempotent if already active.",
)
def activate_product(
    sku: Sku,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.activate_product(actor, sku)


@router.get(
    "/{sku}/movements",
    response_model=MovementPage,
    summary="List stock movements",
    description="Newest movement first. Same visibility rules as GET product.",
    responses={404: {"description": "Unknown SKU, or inactive and you are not an admin."}},
)
def list_movements(
    sku: Sku,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MovementPage:
    return service.list_movements(actor, sku, limit=limit, offset=offset)


@router.post(
    "/{sku}/receive",
    response_model=ProductRead,
    summary="Receive stock",
    description="Adds units. Any signed-in user on an active product. Appends a ledger row.",
    responses={409: {"description": "Product is inactive."}},
)
def receive_stock(
    sku: Sku,
    payload: Annotated[ReceiveStock, Body(openapi_examples=_RECEIVE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.receive_stock(actor, sku, payload)


@router.post(
    "/{sku}/sale",
    response_model=ProductRead,
    summary="Record a sale",
    description=(
        "Removes units. quantity must be positive in the body; the service applies a negative "
        "delta. Returns 409 when quantity_on_hand would go below zero."
    ),
    responses={
        409: {
            "description": "Not enough stock, or the product is inactive.",
        },
    },
)
def sale_stock(
    sku: Sku,
    payload: Annotated[SaleStock, Body(openapi_examples=_SALE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.sale_stock(actor, sku, payload)


@router.post(
    "/{sku}/adjust",
    response_model=ProductRead,
    summary="Adjust stock",
    description=(
        "Signed delta for cycle counts or corrections. Zero delta is 409. "
        "Resulting quantity cannot be negative."
    ),
    responses={409: {"description": "Delta is zero, not enough stock, or product inactive."}},
)
def adjust_stock(
    sku: Sku,
    payload: Annotated[AdjustStock, Body(openapi_examples=_ADJUST_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductRead:
    return service.adjust_stock(actor, sku, payload)

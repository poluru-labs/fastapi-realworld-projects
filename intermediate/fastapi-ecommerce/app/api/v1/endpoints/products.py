from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_optional_user, get_product_service
from app.schemas.product import ProductCreate, ProductRead, ProductStatus, ProductUpdate
from app.schemas.user import UserRead
from app.services.product_service import ProductService

router = APIRouter()

_CREATE_EXAMPLES = {
    "accessory": {
        "summary": "Draft accessory listing",
        "value": {
            "name": "Mechanical Keyboard",
            "summary": "Hot-swappable switches.",
            "description": "Compact layout with RGB backlight.",
            "price_cents": 12999,
            "stock": 25,
            "tags": ["electronics", "keyboards"],
        },
    }
}


@router.get(
    "",
    response_model=list[ProductRead],
    summary="List products",
    description=(
        "Anonymous callers see **active** products only. "
        "Platform admins may pass `status` to include drafts or archived rows."
    ),
)
def list_products(
    service: Annotated[ProductService, Depends(get_product_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    product_status: Annotated[
        ProductStatus | None,
        Query(alias="status", description="Admin-only filter for draft, active, or archived."),
    ] = None,
    tag: Annotated[str | None, Query(description="Filter by tag on active products.")] = None,
    query: Annotated[
        str | None,
        Query(description="Case-insensitive search in name or summary."),
    ] = None,
    max_price_cents: Annotated[
        int | None,
        Query(ge=0, description="Include active products at or below this price."),
    ] = None,
) -> list[ProductRead]:
    return service.list_products(
        actor,
        status=product_status,
        tag=tag,
        query=query,
        max_price_cents=max_price_cents,
    )


@router.get(
    "/{slug}",
    response_model=ProductRead,
    summary="Get one product",
    description=(
        "Active products are public. Draft and archived products return **404** for everyone "
        "except a platform admin."
    ),
)
def get_product(
    slug: str,
    service: Annotated[ProductService, Depends(get_product_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> ProductRead:
    return service.get_product(actor, slug)


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft product (admin)",
)
def create_product(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ProductService, Depends(get_product_service)],
    payload: Annotated[ProductCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> ProductRead:
    return service.create_product(actor, payload)


@router.patch(
    "/{slug}",
    response_model=ProductRead,
    summary="Update a draft product (admin)",
    description="Only **draft** products accept content edits.",
)
def update_product(
    slug: str,
    payload: ProductUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.update_product(actor, slug, payload)


@router.post(
    "/{slug}/activate",
    response_model=ProductRead,
    summary="Activate a draft product (admin)",
)
def activate_product(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.transition(actor, slug, ProductStatus.ACTIVE)


@router.post(
    "/{slug}/deactivate",
    response_model=ProductRead,
    summary="Return an active product to draft (admin)",
)
def deactivate_product(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.transition(actor, slug, ProductStatus.DRAFT)


@router.post(
    "/{slug}/archive",
    response_model=ProductRead,
    summary="Archive a product (admin)",
)
def archive_product(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.transition(actor, slug, ProductStatus.ARCHIVED)


@router.post(
    "/{slug}/restore",
    response_model=ProductRead,
    summary="Restore an archived product to draft (admin)",
)
def restore_product(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.transition(actor, slug, ProductStatus.DRAFT)

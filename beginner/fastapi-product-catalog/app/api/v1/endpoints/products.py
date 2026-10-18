from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_product_service
from app.schemas.product import (
    CategoryListResponse,
    ProductCreate,
    ProductDeleteResponse,
    ProductRead,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter()

_CREATE_EXAMPLES = {
    "cable": {
        "summary": "Add a simple accessory",
        "value": {
            "sku": "cable-usbc-2m",
            "name": "USB-C cable 2m",
            "description": "Braided cable for charging and data.",
            "price": 12.99,
            "category": "accessories",
            "tags": ["usb-c", "cable"],
            "stock_quantity": 50,
            "featured": False,
        },
    }
}


@router.get(
    "/categories",
    response_model=CategoryListResponse,
    summary="List product categories",
    description="Distinct categories from active (non-discontinued) products, sorted A–Z.",
)
def list_categories(
    service: Annotated[ProductService, Depends(get_product_service)],
) -> CategoryListResponse:
    return service.list_categories()


@router.get(
    "/by-sku/{sku}",
    response_model=ProductRead,
    summary="Look up product by SKU",
    description="SKU matching is case-insensitive.",
)
def get_product_by_sku(
    sku: str,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.get_by_sku(sku)


@router.get(
    "",
    response_model=list[ProductRead],
    summary="List products",
    description=(
        "Active catalog by default (`discontinued=false`). Featured products appear first, "
        "then sorted by name. Use `search` to match name, SKU, description, category, or tags."
    ),
)
def list_products(
    service: Annotated[ProductService, Depends(get_product_service)],
    category: Annotated[
        str | None,
        Query(description="Filter by category (exact, case-insensitive)."),
    ] = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
    in_stock: Annotated[
        bool | None,
        Query(description="When set, filter by whether stock_quantity > 0."),
    ] = None,
    featured: Annotated[
        bool | None,
        Query(description="Filter featured or non-featured products."),
    ] = None,
    discontinued: Annotated[
        bool,
        Query(description="When true, list discontinued products only."),
    ] = False,
) -> list[ProductRead]:
    return service.list_products(
        category=category,
        search=search,
        in_stock=in_stock,
        featured=featured,
        discontinued=discontinued,
    )


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    summary="Get product by id",
)
def get_product(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.get_product(product_id)


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="SKUs must be unique (normalized to uppercase for storage and comparison).",
)
def create_product(
    service: Annotated[ProductService, Depends(get_product_service)],
    payload: Annotated[ProductCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> ProductRead:
    return service.create_product(payload)


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    summary="Update product",
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.update_product(product_id, payload)


@router.post(
    "/{product_id}/feature",
    response_model=ProductRead,
    summary="Mark product as featured",
)
def feature_product(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.feature(product_id)


@router.post(
    "/{product_id}/unfeature",
    response_model=ProductRead,
    summary="Remove featured flag",
)
def unfeature_product(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.unfeature(product_id)


@router.post(
    "/{product_id}/discontinue",
    response_model=ProductRead,
    summary="Discontinue product",
    description=(
        "Discontinued products are hidden from the default list until you query "
        "with `discontinued=true`."
    ),
)
def discontinue_product(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.discontinue(product_id)


@router.post(
    "/{product_id}/restore",
    response_model=ProductRead,
    summary="Restore discontinued product",
)
def restore_product(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return service.restore(product_id)


@router.delete(
    "/{product_id}",
    response_model=ProductDeleteResponse,
    summary="Delete product",
)
def delete_product(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDeleteResponse:
    return service.delete_product(product_id)

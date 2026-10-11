from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_product_service
from app.schemas.product import TagCount
from app.services.product_service import ProductService

router = APIRouter()


@router.get(
    "",
    response_model=list[TagCount],
    summary="List tags on active products",
    description=(
        "Public. Counts include active products only. "
        "Tags on drafts are hidden until activation."
    ),
)
def list_tags(
    service: Annotated[ProductService, Depends(get_product_service)],
) -> list[TagCount]:
    return service.list_tags()

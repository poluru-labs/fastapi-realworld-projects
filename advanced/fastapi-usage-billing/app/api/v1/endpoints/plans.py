from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_catalog_service
from app.schemas.plan import PlanRead
from app.services.catalog_service import CatalogService

router = APIRouter()


@router.get(
    "",
    response_model=list[PlanRead],
    summary="List plans",
    description="Each plan defines included units and overage `unit_price_cents` per meter.",
)
async def list_plans(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> list[PlanRead]:
    return await service.list_plans()

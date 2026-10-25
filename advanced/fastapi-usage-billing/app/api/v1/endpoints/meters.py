from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_catalog_service
from app.schemas.meter import MeterRead
from app.services.catalog_service import CatalogService

router = APIRouter()


@router.get(
    "",
    response_model=list[MeterRead],
    summary="List meters",
    description=(
        "Billable metrics configured for this API. Usage events reference `meter_code`. "
        "Seed data includes `api_calls` and `tokens`."
    ),
)
async def list_meters(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> list[MeterRead]:
    return await service.list_meters()

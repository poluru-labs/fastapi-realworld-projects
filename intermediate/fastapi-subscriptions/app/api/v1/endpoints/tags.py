from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_plan_service
from app.schemas.plan import TagCount
from app.services.plan_service import PlanService

router = APIRouter()


@router.get(
    "",
    response_model=list[TagCount],
    summary="List tags on active plans",
    description="Public. Tags on draft plans are hidden until activation.",
)
def list_tags(
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> list[TagCount]:
    return service.list_tags()

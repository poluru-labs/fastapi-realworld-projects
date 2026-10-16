from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_job_service
from app.schemas.job import SkillCount
from app.services.job_service import JobService

router = APIRouter()


@router.get(
    "",
    response_model=list[SkillCount],
    summary="List skills on published jobs",
    description="Public. Counts include published jobs only. Names sorted alphabetically.",
)
def list_skills(
    service: Annotated[JobService, Depends(get_job_service)],
) -> list[SkillCount]:
    return service.list_skills()

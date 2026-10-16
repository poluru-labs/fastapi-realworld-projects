from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_application_service, get_current_user
from app.schemas.application import ApplicationPage
from app.schemas.user import UserRead
from app.services.application_service import ApplicationService

router = APIRouter()


@router.get(
    "/mine",
    response_model=ApplicationPage,
    summary="List your applications",
    description="Every job you applied to, newest first.",
)
def list_my_applications(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApplicationPage:
    return service.list_mine(actor, limit=limit, offset=offset)

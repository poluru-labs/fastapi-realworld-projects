from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_event_service
from app.schemas.event import TagCount
from app.services.event_service import EventService

router = APIRouter()


@router.get(
    "",
    response_model=list[TagCount],
    summary="List tags on published events",
    description=(
        "Public. Counts include published events only. "
        "Tags on drafts are hidden until publish."
    ),
)
def list_tags(
    service: Annotated[EventService, Depends(get_event_service)],
) -> list[TagCount]:
    return service.list_tags()
